from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.paths import ProjectRootPath, resolve_inside_project, resolve_project_root
from llm_tool_cli.paths.errors import InvalidProjectPath, PathResolutionFailed


class TestResolveProjectRoot:
    def test_normalizes_parent_segments(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        project.mkdir()

        assert resolve_project_root(project / ".." / "project" / ".").unwrap() == project

    def test_resolves_relative_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        assert resolve_project_root(Path("project")).unwrap() == tmp_path / "project"

    def test_resolves_current_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        assert resolve_project_root(Path()).unwrap() == tmp_path

    def test_accepts_missing_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "missing" / "project"

        assert resolve_project_root(root).unwrap() == root
        assert not root.exists()

    def test_does_not_validate_directory_kind(self, tmp_path: Path) -> None:
        root = tmp_path / "file"
        root.write_text("", encoding="utf-8")

        assert resolve_project_root(root).unwrap() == root

    def test_does_not_expand_home_marker(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        assert resolve_project_root(Path("~/project")).unwrap() == tmp_path / "~" / "project"

    def test_follows_symlinks(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        root = tmp_path / "link"
        root.symlink_to(target, target_is_directory=True)

        assert resolve_project_root(root).unwrap() == target

    def test_symlink_loop_returns_resolution_failure(self, tmp_path: Path) -> None:
        root = tmp_path / "loop"
        root.symlink_to(root)

        failure = resolve_project_root(root).unwrap_err()[0]

        assert isinstance(failure, PathResolutionFailed)
        assert failure.code == "path_resolution_failed"
        assert failure.path == str(root)
        assert isinstance(failure.cause, (OSError, RuntimeError))
        assert failure.reason == str(failure.cause)

    @pytest.mark.parametrize("original", [PermissionError("permission denied"), RuntimeError("symlink loop")])
    def test_resolution_failure_preserves_cause(
        self, tmp_path: Path, mocker: MockerFixture, original: Exception
    ) -> None:
        mocker.patch.object(Path, "resolve", side_effect=original)

        failures = resolve_project_root(tmp_path).unwrap_err()

        assert len(failures) == 1
        failure = failures[0]
        assert isinstance(failure, PathResolutionFailed)
        assert failure.code == "path_resolution_failed"
        assert failure.path == str(tmp_path)
        assert failure.reason == str(original)
        assert failure.cause == original

    def test_unexpected_exception_propagates(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=ValueError("unexpected failure"))

        with pytest.raises(ValueError, match="unexpected failure"):
            resolve_project_root(tmp_path)


class TestResolveInsideProject:
    def test_resolves_file_and_parent_segments(self, tmp_path: Path) -> None:
        target = tmp_path / "file"
        target.touch()
        path = tmp_path / "nested" / ".." / "file"

        assert resolve_inside_project(path, ProjectRootPath(tmp_path)).unwrap() == target

    def test_accepts_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "directory"
        path.mkdir()

        assert resolve_inside_project(path, ProjectRootPath(tmp_path)).unwrap() == path

    def test_accepts_missing_target(self, tmp_path: Path) -> None:
        path = tmp_path / "missing" / "file"

        assert resolve_inside_project(path, ProjectRootPath(tmp_path)).unwrap() == path
        assert not path.exists()

    def test_resolves_relative_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd = tmp_path / "nested"
        cwd.mkdir()
        monkeypatch.chdir(cwd)

        assert resolve_inside_project(Path("file"), ProjectRootPath(tmp_path)).unwrap() == (cwd / "file")

    def test_does_not_expand_home_marker(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        assert resolve_inside_project(Path("~/file"), ProjectRootPath(tmp_path)).unwrap() == (tmp_path / "~" / "file")

    @pytest.mark.parametrize("relative", [".", "..", "../outside", "../project-sibling/file"])
    def test_rejects_root_and_outside_paths(self, tmp_path: Path, relative: str) -> None:
        root = ProjectRootPath(tmp_path / "project")

        errors = resolve_inside_project(root / relative, root).unwrap_err()

        assert len(errors) == 1
        error = errors[0]
        assert isinstance(error, InvalidProjectPath)
        assert error.code == "invalid_project_path"
        assert error.path == str(root / relative)

    def test_follows_symlink_inside_root(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target, target_is_directory=True)

        assert resolve_inside_project(link / "file", ProjectRootPath(tmp_path)).unwrap() == (target / "file")

    @pytest.mark.parametrize("target", [".", ".."])
    def test_rejects_symlink_to_root_or_outside(self, tmp_path: Path, target: str) -> None:
        link = tmp_path / "link"
        link.symlink_to(tmp_path / target, target_is_directory=True)

        assert resolve_inside_project(link, ProjectRootPath(tmp_path)).unwrap_err() == [
            InvalidProjectPath(path=str(link))
        ]

    def test_symlink_loop_returns_resolution_failure(self, tmp_path: Path) -> None:
        link = tmp_path / "loop"
        link.symlink_to(link)

        failure = resolve_inside_project(link, ProjectRootPath(tmp_path)).unwrap_err()[0]

        assert isinstance(failure, PathResolutionFailed)
        assert failure.path == str(link)
        assert isinstance(failure.cause, (OSError, RuntimeError))

    @pytest.mark.parametrize("cause", [PermissionError(" permission denied "), RuntimeError(" symlink loop ")])
    def test_resolution_failure_preserves_diagnostic_and_private_cause(
        self, tmp_path: Path, mocker: MockerFixture, cause: Exception
    ) -> None:
        mocker.patch.object(Path, "resolve", side_effect=cause)

        errors = resolve_inside_project(tmp_path / "file", ProjectRootPath(tmp_path)).unwrap_err()

        assert len(errors) == 1
        failure = errors[0]
        assert isinstance(failure, PathResolutionFailed)
        assert failure.cause == cause
        assert failure.as_record() == {
            "type": "error",
            "code": "path_resolution_failed",
            "message": failure.format_message(),
            "path": str(tmp_path / "file"),
            "reason": str(cause).strip(),
        }

    def test_unexpected_exception_propagates(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=ValueError("unexpected failure"))

        with pytest.raises(ValueError, match="unexpected failure"):
            resolve_inside_project(tmp_path / "file", ProjectRootPath(tmp_path))
