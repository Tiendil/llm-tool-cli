from pathlib import Path

import pytest
from filelock import FileLock, Timeout
from pytest_mock import MockerFixture

from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.file_locks import errors as lock_errors
from llm_tool_cli.file_locks.tests.helpers import held_lock
from llm_tool_cli.paths import PathInput
from llm_tool_cli.paths import errors as path_errors
from llm_tool_cli.tool_state import StateRootPath, ToolStateDirectory, errors


class TestToolStateDirectory:
    def test_for_tool__discovers_and_resolves_without_creating(self, tmp_path: Path, mocker: MockerFixture) -> None:
        actual = tmp_path / "actual"
        actual.mkdir()
        alias = tmp_path / "alias"
        alias.symlink_to(actual, target_is_directory=True)
        discover = mocker.patch("llm_tool_cli.tool_state.directory.user_state_path", return_value=alias / "sample")

        state = ToolStateDirectory.for_tool(ToolName(" sample ")).unwrap()

        assert state.root == actual / "sample"
        discover.assert_called_once_with("sample", appauthor=False, ensure_exists=False)
        assert not state.root.exists()

    @pytest.mark.parametrize("failure", [OSError("unavailable"), RuntimeError("unavailable"), Path("relative")])
    def test_for_tool__does_not_fall_back(
        self, tmp_path: Path, mocker: MockerFixture, failure: Exception | Path
    ) -> None:
        mocker.patch(
            "llm_tool_cli.tool_state.directory.user_state_path",
            **({"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}),
        )
        problem = ToolStateDirectory.for_tool(ToolName("sample")).unwrap_err()[0]
        assert isinstance(problem, errors.StateDirectoryUnavailable)
        assert problem.tool_name == "sample"
        assert problem.path == (None if isinstance(failure, Exception) else failure)
        assert problem.cause == (failure if isinstance(failure, Exception) else None)
        assert not list(tmp_path.iterdir())

    def test_for_tool__preserves_resolution_errors(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cause = PermissionError("unavailable")
        mocker.patch("llm_tool_cli.tool_state.directory.user_state_path", return_value=tmp_path / "state")
        mocker.patch("pathlib.Path.resolve", side_effect=cause)
        problem = ToolStateDirectory.for_tool(ToolName("sample")).unwrap_err()[0]
        assert isinstance(problem, path_errors.PathResolutionFailed)
        assert problem.cause == cause

    def test_resolve__contains_relative_paths_without_creating(self, tmp_path: Path) -> None:
        state = ToolStateDirectory(StateRootPath(tmp_path / "state"))
        selected = state.resolve(PathInput(Path("locks") / "job.lock")).unwrap()
        assert selected == tmp_path / "state" / "locks" / "job.lock"
        assert not state.root.exists()

    @pytest.mark.parametrize("absolute", [False, True])
    def test_resolve__rejects_escapes_and_absolute_paths(self, tmp_path: Path, absolute: bool) -> None:
        state = ToolStateDirectory(StateRootPath(tmp_path / "state"))
        relative = state.root / "job.lock" if absolute else Path("../job.lock")
        with state.lock(PathInput(relative), timeout=0) as result:
            assert isinstance(result.unwrap_err()[0], path_errors.InvalidProjectPath)
        assert not list(tmp_path.iterdir())

    def test_resolve__rejects_links_below_root(self, tmp_path: Path) -> None:
        state = ToolStateDirectory(StateRootPath(tmp_path))
        (tmp_path / "alias").symlink_to(tmp_path, target_is_directory=True)
        result = state.resolve(PathInput(Path("alias/job.lock")))
        assert isinstance(result.unwrap_err()[0], path_errors.InvalidProjectPath)

    def test_lock__creates_parents_retains_file_and_releases_on_exception(self, tmp_path: Path) -> None:
        state = ToolStateDirectory(StateRootPath(tmp_path / "state"))
        relative = PathInput(Path("locks/job.lock"))
        selected = state.resolve(relative).unwrap()

        with pytest.raises(RuntimeError, match="body failure"), state.lock(relative, timeout=0) as result:
            result.unwrap()
            assert selected.is_file()
            with pytest.raises(Timeout), FileLock(selected, timeout=0, preserve_lock_file=True):
                pass
            raise RuntimeError("body failure")

        assert selected.is_file()
        with FileLock(selected, timeout=0, preserve_lock_file=True):
            pass

    def test_lock__names_are_independent_and_failures_keep_native_context(self, tmp_path: Path) -> None:
        state = ToolStateDirectory(StateRootPath(tmp_path))
        selected = state.resolve(PathInput(Path("first.lock"))).unwrap()
        with held_lock(selected):
            with state.lock(PathInput(Path("first.lock")), timeout=0) as blocked:
                problem = blocked.unwrap_err()[0]
                assert isinstance(problem, lock_errors.Timeout)
                assert problem.path == selected
                assert isinstance(problem.cause, Timeout)
            with state.lock(PathInput(Path("second.lock")), timeout=0) as independent:
                independent.unwrap()
