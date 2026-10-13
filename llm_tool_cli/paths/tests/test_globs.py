from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.paths import FileGlobPattern, ProjectPathId, ProjectRootPath, glob_capture_names, match_glob
from llm_tool_cli.paths.errors import InvalidGlobPattern, InvalidProjectPath, PathResolutionFailed
from llm_tool_cli.paths.globs import _compile_glob, _pattern_parts


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

    def test_resolution_failure_retains_the_cause(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cause = PermissionError("denied")
        mocker.patch.object(Path, "resolve", side_effect=cause)

        failure = _pattern_parts(FileGlobPattern("src/*.py"), ProjectRootPath(tmp_path)).unwrap_err()[0]

        assert isinstance(failure, PathResolutionFailed)
        assert failure.path == str(tmp_path / "src/*.py")
        assert failure.cause == cause

    @pytest.mark.parametrize("pattern", ["", ".", "../*", "@/../*", "@/", "@/a//b"])
    def test_invalid_path_is_not_a_pattern(self, tmp_path: Path, pattern: str) -> None:
        assert _pattern_parts(FileGlobPattern(pattern), ProjectRootPath(tmp_path)).is_err(InvalidProjectPath)


class TestCompileGlob:
    @pytest.mark.parametrize(
        ("pattern", "matching", "nonmatching", "recursive"),
        [
            ("*.py", "a.py", "dir/a.py", False),
            ("a?.py", "a1.py", "a/1.py", False),
            ("[ab].py", "a.py", "c.py", False),
            ("[!a].py", "b.py", "a.py", False),
            ("[a-z].py", "b.py", "B.py", False),
            ("star[*].py", "star*.py", "starfile.py", False),
            ("[[]file].py", "[file].py", "file.py", False),
            ("[]].py", "].py", "a.py", False),
            ("[**].py", "*.py", "dir/a.py", False),
            ("[abc", "[abc", "a", False),
            ("[a/b]", "[a/b]", "a", False),
            ("**/*.py", "a.py", "a.txt", True),
            ("a**.py", "a/deep/file.py", "b.py", True),
            ("**", "line\nbreak.py", "", True),
            ("{variable}", "{variable}", "value", False),
            ("a\\b", "a\\b", "a/b", False),
        ],
    )
    def test_wildcard_semantics(self, pattern: str, matching: str, nonmatching: str, recursive: bool) -> None:
        compiled, actual_recursive = _compile_glob(FileGlobPattern(pattern)).unwrap()

        assert compiled.fullmatch(matching) is not None
        if nonmatching:
            assert compiled.fullmatch(nonmatching) is None
        assert actual_recursive == recursive

    @pytest.mark.parametrize("pattern", ["{*bad-name}", "{**}", "{***name}", "{*unclosed", "{*x}/{**x}"])
    def test_invalid_captures_return_diagnostics(self, pattern: str) -> None:
        failure = _compile_glob(FileGlobPattern(pattern)).unwrap_err()[0]

        assert isinstance(failure, InvalidGlobPattern)
        assert failure.code == "invalid_glob_pattern"
        assert failure.pattern == pattern
        assert failure.reason


class TestGlobCaptureNames:
    def test_extracts_captures_without_interpreting_templates_or_escaped_stars(self) -> None:
        assert glob_capture_names(FileGlobPattern("{base}/{**package}/{*module}.py")).unwrap() == {
            "package",
            "module",
        }
        assert glob_capture_names(FileGlobPattern("{[*]literal}.py")).unwrap() == set()
        assert glob_capture_names(FileGlobPattern("")).unwrap() == set()

    def test_invalid_capture_names_are_rejected(self) -> None:
        assert glob_capture_names(FileGlobPattern("{*bad-name}")).is_err(InvalidGlobPattern)


class TestMatchGlob:
    @pytest.mark.parametrize(
        ("pattern", "path", "expected"),
        [
            ("src/{**package}/{*module}.py", "@/src/core/api.py", {"package": "core", "module": "api"}),
            ("src/{**package}/{*module}.py", "@/src/api.py", {"package": "", "module": "api"}),
            ("src/{**module_path}.py", "@/src/core/api.py", {"module_path": "core/api"}),
            ("src/{**module_path}.py", "@/src/api.py", {"module_path": "api"}),
            ("src/{*module}.py", "@/src/core/api.py", None),
            ("src/{*module}.py", "@/src/.py", {"module": ""}),
            ("src/{**package}/{*module}.py", "@/src/one/two/api.py", {"package": "one/two", "module": "api"}),
            ("src/*.py", "@/src/file.py", {}),
            ("src/**", "@/src", None),
        ],
    )
    def test_matches_missing_references(
        self, tmp_path: Path, pattern: str, path: str, expected: dict[str, str] | None
    ) -> None:
        assert match_glob(ProjectPathId(path), FileGlobPattern(pattern), tmp_path).unwrap() == expected

    def test_does_not_resolve_glob_syntax_as_a_symlink(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src/*.py").symlink_to(tmp_path / "missing")

        assert match_glob(ProjectPathId("@/src/a.py"), FileGlobPattern("@/src/*.py"), tmp_path).unwrap() == {}

    @pytest.mark.parametrize("pattern", ["link/*.py", "link/../*.py", "@/link/*.py"])
    def test_literal_symlink_prefix_is_rejected(self, tmp_path: Path, pattern: str) -> None:
        (tmp_path / "link").symlink_to(tmp_path)

        assert match_glob(ProjectPathId("@/a.py"), FileGlobPattern(pattern), tmp_path).is_err(InvalidProjectPath)

    def test_root_resolution_precedes_pattern_validation(self, tmp_path: Path) -> None:
        root = tmp_path / "loop"
        root.symlink_to(root)

        assert match_glob(ProjectPathId("@/a.py"), FileGlobPattern("@/../*"), root).is_err(PathResolutionFailed)

    def test_absolute_and_home_patterns(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        for pattern in [str(tmp_path / "*.py"), "~/*.py"]:
            assert match_glob(ProjectPathId("@/a.py"), FileGlobPattern(pattern), tmp_path).unwrap() == {}

    def test_syntax_failures_are_preserved(self, tmp_path: Path) -> None:
        assert match_glob(ProjectPathId("@/a.py"), FileGlobPattern("{*bad-name}"), tmp_path).is_err(InvalidGlobPattern)
