import glob
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.paths import FileGlobPattern, ProjectRootPath, enumerate_files
from llm_tool_cli.paths.enumeration import _glob_files, _pattern_parts
from llm_tool_cli.paths.errors import FilesUnreadable, InvalidProjectPath, PathResolutionFailed


class TestPatternParts:
    def test_resolves_literal_prefix_before_normalizing_remaining_parts(self, tmp_path: Path) -> None:
        assert _pattern_parts(FileGlobPattern("nested/../**/*.py"), ProjectRootPath(tmp_path)).unwrap() == (
            "**",
            "*.py",
        )

    def test_root_metacharacters_are_literal(self, tmp_path: Path) -> None:
        root = tmp_path / "[project]*?"
        root.mkdir()
        (root / "link").symlink_to(root)

        assert _pattern_parts(FileGlobPattern("link/*.py"), ProjectRootPath(root)).is_err(InvalidProjectPath)


class TestGlobFiles:
    def test_recursive_patterns_dedicated_components(self, tmp_path: Path) -> None:
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested/a.py").touch()
        (tmp_path / "b.py").touch()
        (tmp_path / "broken.py").symlink_to(tmp_path / "absent")

        assert sorted(_glob_files(tmp_path, ("**", "*.py"))) == [tmp_path / "b.py", tmp_path / "nested/a.py"]

    def test_missing_or_non_directory_prefix_has_no_matches(self, tmp_path: Path) -> None:
        (tmp_path / "file").touch()

        assert list(_glob_files(tmp_path / "missing", ("*",))) == []
        assert list(_glob_files(tmp_path / "file/child", ("*",))) == []
        assert list(_glob_files(tmp_path / "file", ("*",))) == []


class TestEnumerateFiles:
    def test_wildcards_do_not_resolve_literal_symlink_names(self, tmp_path: Path) -> None:
        (tmp_path / "ordinary").touch()
        (tmp_path / "*").symlink_to(tmp_path)
        (tmp_path / "**").symlink_to(tmp_path)

        assert enumerate_files(tmp_path).unwrap() == ["@/ordinary"]

    @pytest.mark.parametrize("pattern", ["**/*", "@/**/*", "**", "**/**"])
    def test_unique_files_in_component_order_including_hidden_entries(self, tmp_path: Path, pattern: str) -> None:
        names = ["a/child", "a.txt", ".hidden/file", ".hidden-file", "z"]
        for name in names:
            path = tmp_path / name
            path.parent.mkdir(exist_ok=True)
            path.touch()
        (tmp_path / "empty").mkdir()

        assert enumerate_files(tmp_path, FileGlobPattern(pattern)).unwrap() == [
            "@/.hidden/file",
            "@/.hidden-file",
            "@/a/child",
            "@/a.txt",
            "@/z",
        ]

    @pytest.mark.parametrize("pattern", ["**/*.py", "@/**/*.py", "**/a?.[pt][xy]", "**/[!b]*.py"])
    def test_glob_syntax_and_zero_directory_recursion(self, tmp_path: Path, pattern: str) -> None:
        (tmp_path / "nested").mkdir()
        for name in ["a1.py", "nested/a2.py", "b.txt"]:
            (tmp_path / name).touch()

        assert enumerate_files(tmp_path, FileGlobPattern(pattern)).unwrap() == ["@/a1.py", "@/nested/a2.py"]

    @pytest.mark.parametrize("pattern", ["**/*", "**", "*.py", "*/**/*"])
    def test_skips_all_discovered_links(self, tmp_path: Path, pattern: str) -> None:
        project = tmp_path / "project"
        project.mkdir()
        target = tmp_path / "outside"
        target.mkdir()
        (target / "outside.py").touch()
        (project / "ordinary.py").touch()
        for name, destination in [
            ("file.py", project / "ordinary.py"),
            ("external.py", target / "outside.py"),
            ("directory", target),
            ("cycle", project),
            ("broken.py", project / "missing"),
        ]:
            (project / name).symlink_to(destination)

        expected = [] if pattern == "*/**/*" else ["@/ordinary.py"]
        assert enumerate_files(project, FileGlobPattern(pattern)).unwrap() == expected

    @pytest.mark.parametrize("suffix", ["", "/**/*", "/../ordinary"])
    def test_rejects_explicit_symlink_prefix(self, tmp_path: Path, suffix: str) -> None:
        (tmp_path / "link").symlink_to(tmp_path)
        result = enumerate_files(tmp_path, FileGlobPattern("link" + suffix))

        assert result.is_err(InvalidProjectPath)

    def test_missing_directory_or_file_root_produces_no_files(self, tmp_path: Path) -> None:
        (tmp_path / "file").touch()

        assert enumerate_files(tmp_path, FileGlobPattern("missing/**/*")).unwrap() == []
        assert enumerate_files(tmp_path / "missing").unwrap() == []
        assert enumerate_files(tmp_path / "file").unwrap() == []

    def test_literal_pattern_and_escaped_metacharacters(self, tmp_path: Path) -> None:
        directory = tmp_path / "[work]*?"
        directory.mkdir()
        (directory / "file.py").touch()

        assert enumerate_files(tmp_path, FileGlobPattern(glob.escape(directory.name) + "/file.py")).unwrap() == [
            "@/[work]*?/file.py"
        ]

    def test_absolute_and_home_patterns(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / "file.py").touch()

        assert enumerate_files(tmp_path, FileGlobPattern(str(tmp_path / "*.py"))).unwrap() == ["@/file.py"]
        assert enumerate_files(tmp_path, FileGlobPattern("~/*.py")).unwrap() == ["@/file.py"]

    @pytest.mark.parametrize("pattern", ["../*", "@/../*", "@/", "@/a//b", "."])
    def test_invalid_patterns_preserve_diagnostics(self, tmp_path: Path, pattern: str) -> None:
        assert enumerate_files(tmp_path, FileGlobPattern(pattern)).is_err(InvalidProjectPath)

    def test_root_resolution_failure_precedes_pattern_processing(self, tmp_path: Path) -> None:
        root = tmp_path / "loop"
        root.symlink_to(root)

        assert enumerate_files(root, FileGlobPattern("@/../*")).is_err(PathResolutionFailed)

    def test_directory_read_failure_is_not_an_empty_result(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cause = PermissionError("cannot list directory")
        mocker.patch.object(Path, "iterdir", side_effect=cause)

        failure = enumerate_files(tmp_path).unwrap_err()[0]

        assert isinstance(failure, FilesUnreadable)
        assert failure.code == "files_unreadable"
        assert failure.path == str(tmp_path)
        assert failure.cause == cause
        assert "cause" not in failure.as_record()

    def test_unexpected_failure_remains_an_exception(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "iterdir", side_effect=ValueError("unexpected failure"))

        with pytest.raises(ValueError, match="unexpected failure"):
            enumerate_files(tmp_path)
