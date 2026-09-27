from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.paths import (
    ProjectRootPath,
    normalize_path,
    project_path_id_from_filesystem,
    project_path_id_from_resolved,
    resolve_inside_project,
    resolve_project_root,
    resolve_root_anchored_path,
)
from llm_tool_cli.paths.errors import InvalidProjectPath, PathResolutionFailed


class TestNormalizePath:
    @pytest.mark.parametrize("value", ["@/nested/./child/../file", "@/nested/file"])
    def test_normalizes_identifier(self, tmp_path: Path, value: str) -> None:
        assert normalize_path(value, tmp_path).unwrap() == "@/nested/file"

    @pytest.mark.parametrize("value", ["@file", "@/", "@/a/..", "@/../file", "@/a//b", "@/a/"])
    def test_preserves_invalid_identifier_diagnostic(self, tmp_path: Path, value: str) -> None:
        assert normalize_path(value, tmp_path).unwrap_err() == [InvalidProjectPath(path=value)]

    @pytest.mark.parametrize("kind", ["file", "directory", "missing"])
    def test_accepts_filesystem_target_without_kind_requirements(self, tmp_path: Path, kind: str) -> None:
        target = tmp_path / "target"
        if kind == "file":
            target.touch()
        elif kind == "directory":
            target.mkdir()

        assert normalize_path(str(target), tmp_path).unwrap() == "@/target"

    def test_default_base_is_resolved_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        assert normalize_path("file", Path("project")).unwrap() == "@/file"

    def test_explicit_base_is_independent_of_process_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path.parent)

        assert normalize_path("file", tmp_path, cwd=tmp_path / "nested").unwrap() == "@/nested/file"

    def test_relative_base_uses_process_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        assert normalize_path("file", tmp_path, cwd=Path("nested")).unwrap() == "@/nested/file"

    def test_absolute_input_ignores_base(self, tmp_path: Path) -> None:
        assert normalize_path(str(tmp_path / "file"), tmp_path, cwd=tmp_path.parent).unwrap() == "@/file"

    def test_identifier_ignores_base_and_target_symlinks(self, tmp_path: Path) -> None:
        (tmp_path / "outside").symlink_to(tmp_path.parent, target_is_directory=True)

        assert normalize_path("@/outside/file", tmp_path, cwd=tmp_path.parent).unwrap() == "@/outside/file"

    def test_filesystem_input_uses_resolved_symlink_target(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (tmp_path / "link").symlink_to(target, target_is_directory=True)

        assert normalize_path("link/file", tmp_path).unwrap() == "@/target/file"

    def test_filesystem_input_rejects_symlink_escape(self, tmp_path: Path) -> None:
        link = tmp_path / "outside"
        link.symlink_to(tmp_path.parent, target_is_directory=True)

        assert normalize_path("outside/file", tmp_path).unwrap_err() == [InvalidProjectPath(path=str(link / "file"))]

    @pytest.mark.parametrize("value", ["", ".", "nested/..", "../outside"])
    def test_rejects_root_and_outside_filesystem_inputs(self, tmp_path: Path, value: str) -> None:
        assert normalize_path(value, tmp_path).unwrap_err() == [InvalidProjectPath(path=str(tmp_path / value))]

    def test_empty_input_identifies_explicit_non_root_base(self, tmp_path: Path) -> None:
        assert normalize_path("", tmp_path, cwd=tmp_path / "nested").unwrap() == "@/nested"

    def test_relative_root_uses_absolute_candidate_in_diagnostic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        assert normalize_path("../outside", Path("project")).unwrap_err() == [
            InvalidProjectPath(path=str(tmp_path / "project" / ".." / "outside"))
        ]

    def test_expands_home_marker(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))

        assert normalize_path("~/project/file", tmp_path / "project").unwrap() == "@/file"

    def test_expanded_home_must_be_inside_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))

        assert normalize_path("~/file", tmp_path / "project").unwrap_err() == [
            InvalidProjectPath(path=str(tmp_path / "file"))
        ]

    def test_accepts_literal_home_marker_segment(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path.parent))

        assert normalize_path("@/~/file", tmp_path).unwrap() == "@/~/file"

    def test_preserves_segment_text(self, tmp_path: Path) -> None:
        value = " notes /Заметки проекта.md "

        assert normalize_path(value, tmp_path).unwrap() == "@/" + value

    @pytest.mark.parametrize("value", ["@/file", "@/../file", "file", "~/file"])
    def test_root_resolution_failure_precedes_input_processing(self, tmp_path: Path, value: str) -> None:
        root = tmp_path / "loop"
        root.symlink_to(root)

        failure = normalize_path(value, root).unwrap_err()[0]

        assert isinstance(failure, PathResolutionFailed)
        assert failure.path == str(root)
        assert isinstance(failure.cause, (OSError, RuntimeError))

    def test_target_resolution_failure_preserves_diagnostic(self, tmp_path: Path) -> None:
        link = tmp_path / "loop"
        link.symlink_to(link)

        failure = normalize_path("loop/file", tmp_path).unwrap_err()[0]

        assert isinstance(failure, PathResolutionFailed)
        assert failure.path == str(link / "file")
        assert isinstance(failure.cause, (OSError, RuntimeError))

    @pytest.mark.parametrize("cause", [RuntimeError("unknown home"), OSError("home lookup failed")])
    def test_home_expansion_failure_preserves_diagnostic(
        self, tmp_path: Path, mocker: MockerFixture, cause: Exception
    ) -> None:
        mocker.patch.object(Path, "expanduser", side_effect=cause)

        failures = normalize_path("~/file", tmp_path).unwrap_err()

        assert len(failures) == 1
        failure = failures[0]
        assert isinstance(failure, PathResolutionFailed)
        assert failure.code == "path_resolution_failed"
        assert failure.path == "~/file"
        assert failure.reason == str(cause)
        assert failure.cause == cause
        assert "cause" not in failure.as_record()

    def test_unexpected_exception_propagates(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "expanduser", side_effect=ValueError("unexpected failure"))

        with pytest.raises(ValueError, match="unexpected failure"):
            normalize_path("file", tmp_path)


class TestProjectPathIdFromFilesystem:
    @pytest.mark.parametrize("kind", ["file", "directory", "missing"])
    def test_converts_filesystem_path(self, tmp_path: Path, kind: str) -> None:
        path = tmp_path / "target"
        if kind == "file":
            path.touch()
        elif kind == "directory":
            path.mkdir()

        assert project_path_id_from_filesystem(path, tmp_path).unwrap() == "@/target"

    def test_preserves_segment_text(self, tmp_path: Path) -> None:
        path = tmp_path / " notes " / "Заметки проекта.md "

        assert project_path_id_from_filesystem(path, tmp_path).unwrap() == "@/ notes /Заметки проекта.md "

    def test_relative_root_and_path_use_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)

        assert project_path_id_from_filesystem(Path("project/file"), Path("project")).unwrap() == "@/file"

    def test_relative_path_uses_cwd_instead_of_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cwd = tmp_path / "nested"
        cwd.mkdir()
        monkeypatch.chdir(cwd)

        assert project_path_id_from_filesystem(Path("file"), tmp_path).unwrap() == "@/nested/file"

    @pytest.mark.parametrize("name", ["~", "@"])
    def test_treats_markers_as_filesystem_segments(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        monkeypatch.chdir(tmp_path)

        assert project_path_id_from_filesystem(Path(name) / "file", tmp_path).unwrap() == f"@/{name}/file"

    def test_resolves_root_symlink(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        link = tmp_path / "link"
        link.symlink_to(root, target_is_directory=True)

        assert project_path_id_from_filesystem(link / "file", link).unwrap() == "@/file"

    def test_uses_resolved_target_identifier(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target, target_is_directory=True)

        assert project_path_id_from_filesystem(link / "file", tmp_path).unwrap() == "@/target/file"

    def test_resolves_parent_segments(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / ".." / "file"

        assert project_path_id_from_filesystem(path, tmp_path).unwrap() == "@/file"

    @pytest.mark.parametrize("relative", [".", "..", "../outside"])
    def test_rejects_root_and_outside_paths(self, tmp_path: Path, relative: str) -> None:
        path = tmp_path / relative

        assert project_path_id_from_filesystem(path, tmp_path).unwrap_err() == [InvalidProjectPath(path=str(path))]

    def test_rejects_symlink_outside_root(self, tmp_path: Path) -> None:
        link = tmp_path / "link"
        link.symlink_to(tmp_path.parent, target_is_directory=True)
        path = link / "file"

        assert project_path_id_from_filesystem(path, tmp_path).unwrap_err() == [InvalidProjectPath(path=str(path))]

    @pytest.mark.parametrize("failing_part", ["root", "target"])
    def test_preserves_resolution_failure(self, tmp_path: Path, failing_part: str) -> None:
        link = tmp_path / "loop"
        link.symlink_to(link)
        root = link if failing_part == "root" else tmp_path
        path = tmp_path / "file" if failing_part == "root" else link

        failures = project_path_id_from_filesystem(path, root).unwrap_err()

        assert len(failures) == 1
        failure = failures[0]
        assert isinstance(failure, PathResolutionFailed)
        assert failure.code == "path_resolution_failed"
        assert failure.path == str(link)
        assert isinstance(failure.cause, (OSError, RuntimeError))
        assert failure.reason == str(failure.cause)

    def test_unexpected_exception_propagates(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=ValueError("unexpected failure"))

        with pytest.raises(ValueError, match="unexpected failure"):
            project_path_id_from_filesystem(tmp_path / "file", tmp_path)


class TestProjectPathIdFromResolved:
    @pytest.mark.parametrize("kind", ["file", "directory", "missing"])
    def test_converts_resolved_path(self, tmp_path: Path, kind: str) -> None:
        path = tmp_path / "target"
        if kind == "file":
            path.touch()
        elif kind == "directory":
            path.mkdir()
        root = resolve_project_root(tmp_path).unwrap()
        resolved = resolve_inside_project(path, root).unwrap()

        assert project_path_id_from_resolved(resolved, root) == "@/target"

    @pytest.mark.parametrize(
        "relative",
        [
            "nested/file.txt",
            "README",
            "Case/FILE",
            " notes /Заметки проекта.md ",
            r"a\b/file",
            "name:section",
            "~/file",
        ],
    )
    def test_preserves_segment_text(self, tmp_path: Path, relative: str) -> None:
        root = resolve_project_root(tmp_path).unwrap()
        resolved = resolve_inside_project(tmp_path / relative, root).unwrap()

        assert project_path_id_from_resolved(resolved, root) == "@/" + relative

    def test_uses_resolved_symlink_target(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (tmp_path / "link").symlink_to(target, target_is_directory=True)
        root = resolve_project_root(tmp_path).unwrap()
        resolved = resolve_root_anchored_path("@/link/file.txt", root).unwrap()

        assert project_path_id_from_resolved(resolved, root) == "@/target/file.txt"

    def test_uses_root_independently_of_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = resolve_project_root(tmp_path / "project").unwrap()
        resolved = resolve_inside_project(root / "file.txt", root).unwrap()
        monkeypatch.chdir(tmp_path)

        assert project_path_id_from_resolved(resolved, root) == "@/file.txt"

    def test_does_not_access_filesystem(self, tmp_path: Path, mocker: MockerFixture) -> None:
        root = resolve_project_root(tmp_path).unwrap()
        resolved = resolve_inside_project(root / "file.txt", root).unwrap()
        mocker.patch.object(Path, "resolve", side_effect=AssertionError("unexpected path resolution"))
        mocker.patch.object(Path, "stat", side_effect=AssertionError("unexpected filesystem access"))

        assert project_path_id_from_resolved(resolved, root) == "@/file.txt"


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


class TestResolveRootAnchoredPath:
    def test_resolves_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "file"
        target.touch()

        assert resolve_root_anchored_path("@/file", ProjectRootPath(tmp_path)).unwrap() == target

    def test_accepts_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "directory"
        target.mkdir()

        assert resolve_root_anchored_path("@/directory", ProjectRootPath(tmp_path)).unwrap() == target

    @pytest.mark.parametrize("relative", ["missing/file", "LICENSE", "notes/Заметки проекта.md", "~/file"])
    def test_accepts_missing_target_and_preserves_segment_text(self, tmp_path: Path, relative: str) -> None:
        target = tmp_path / relative

        assert resolve_root_anchored_path("@/" + relative, ProjectRootPath(tmp_path)).unwrap() == target
        assert not target.exists()

    def test_uses_root_independently_of_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "project"
        cwd = tmp_path / "elsewhere"
        cwd.mkdir()
        monkeypatch.chdir(cwd)

        assert resolve_root_anchored_path("@/file", ProjectRootPath(root)).unwrap() == root / "file"

    def test_normalizes_before_resolving_symlinks(self, tmp_path: Path) -> None:
        (tmp_path / "outside").symlink_to(tmp_path.parent, target_is_directory=True)

        assert (
            resolve_root_anchored_path("@/./outside/../file", ProjectRootPath(tmp_path)).unwrap() == tmp_path / "file"
        )

    @pytest.mark.parametrize("value", ["", "file", "@file", "@/", "@/a/..", "@/a//b", "@/a/", "@/../a"])
    def test_invalid_identifier_preserves_lexical_diagnostic(self, tmp_path: Path, value: str) -> None:
        failures = resolve_root_anchored_path(value, ProjectRootPath(tmp_path)).unwrap_err()

        assert len(failures) == 1
        failure = failures[0]
        assert isinstance(failure, InvalidProjectPath)
        assert failure.code == "invalid_project_path"
        assert failure.path == value

    def test_follows_symlink_inside_root(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.mkdir()
        (tmp_path / "link").symlink_to(target, target_is_directory=True)

        assert resolve_root_anchored_path("@/link/file", ProjectRootPath(tmp_path)).unwrap() == target / "file"

    @pytest.mark.parametrize("target", [".", ".."])
    def test_rejects_symlink_to_root_or_outside(self, tmp_path: Path, target: str) -> None:
        link = tmp_path / "link"
        link.symlink_to(tmp_path / target, target_is_directory=True)

        failures = resolve_root_anchored_path("@/link", ProjectRootPath(tmp_path)).unwrap_err()

        assert len(failures) == 1
        failure = failures[0]
        assert isinstance(failure, InvalidProjectPath)
        assert failure.code == "invalid_project_path"
        assert failure.path == str(link)

    def test_symlink_loop_preserves_resolution_failure(self, tmp_path: Path) -> None:
        link = tmp_path / "loop"
        link.symlink_to(link)

        failures = resolve_root_anchored_path("@/loop/file", ProjectRootPath(tmp_path)).unwrap_err()

        assert len(failures) == 1
        failure = failures[0]
        assert isinstance(failure, PathResolutionFailed)
        assert failure.code == "path_resolution_failed"
        assert failure.path == str(link / "file")
        assert isinstance(failure.cause, (OSError, RuntimeError))

    def test_permission_failure_preserves_diagnostic_and_private_cause(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        cause = PermissionError(" permission denied ")
        mocker.patch.object(Path, "resolve", side_effect=cause)

        failures = resolve_root_anchored_path("@/file", ProjectRootPath(tmp_path)).unwrap_err()

        assert len(failures) == 1
        failure = failures[0]
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
            resolve_root_anchored_path("@/file", ProjectRootPath(tmp_path))
