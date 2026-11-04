import hashlib
import os
from pathlib import Path

import pytest
from filelock import FileLock, Timeout
from pytest_mock import MockerFixture

from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.file_locks import errors as lock_errors
from llm_tool_cli.file_locks.tests.helpers import held_lock
from llm_tool_cli.paths import ProjectRootPath
from llm_tool_cli.paths import errors as path_errors
from llm_tool_cli.paths import resolve_project_root
from llm_tool_cli.tool_state import ToolStateDirectory, errors
from llm_tool_cli.tool_state.project_locks import project_lock, project_lock_path


class TestProjectLockPath:
    def test_stable_project_identity_and_independent_tools(self, tmp_path: Path, mocker: MockerFixture) -> None:
        state_root = tmp_path / "state"
        mocker.patch.dict("os.environ", {"XDG_STATE_HOME": str(state_root)})
        state = ToolStateDirectory.for_tool(ToolName("sample")).unwrap()
        root = ProjectRootPath(tmp_path / "project")
        digest = hashlib.sha256(os.fsencode(os.path.normcase(str(root)))).hexdigest()
        selected = project_lock_path(state, root).unwrap()
        assert selected == state_root / "sample" / "projects" / digest / "operation.lock"
        assert project_lock_path(state, ProjectRootPath(tmp_path / "other")).unwrap() != selected
        other = ToolStateDirectory.for_tool(ToolName("another")).unwrap()
        assert project_lock_path(other, root).unwrap() != selected
        assert not list(tmp_path.iterdir())


class TestProjectLock:
    name = ToolName("sample")

    def test_root_aliases_contend_and_release(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.dict("os.environ", {"XDG_STATE_HOME": str(tmp_path / "state")})
        root = ProjectRootPath(tmp_path / "project")
        root.mkdir()
        alias = tmp_path / "alias"
        alias.symlink_to(root, target_is_directory=True)
        selected = project_lock_path(ToolStateDirectory.for_tool(self.name).unwrap(), root).unwrap()
        selected.parent.mkdir(parents=True)
        with held_lock(selected):
            with project_lock(self.name, resolve_project_root(alias).unwrap(), timeout=0) as blocked:
                problem = blocked.unwrap_err()[0]
                assert isinstance(problem, lock_errors.Timeout)
                assert problem.path == selected
                assert problem.timeout == 0
                assert isinstance(problem.cause, Timeout)
            with project_lock(self.name, ProjectRootPath(tmp_path / "other"), timeout=0) as independent:
                independent.unwrap()
        with project_lock(self.name, root, timeout=0) as acquired:
            acquired.unwrap()
            with pytest.raises(Timeout), FileLock(selected, timeout=0, preserve_lock_file=True):
                pass
        with FileLock(selected, timeout=0, preserve_lock_file=True):
            pass

    @pytest.mark.parametrize("failure", [OSError("unavailable"), RuntimeError("unavailable"), Path("relative")])
    def test_discovery_failure_retains_state_diagnostic(
        self, tmp_path: Path, mocker: MockerFixture, failure: Exception | Path
    ) -> None:
        mocker.patch(
            "llm_tool_cli.tool_state.directory.user_state_path",
            **({"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}),
        )
        with project_lock(self.name, ProjectRootPath(tmp_path), timeout=0) as result:
            problem = result.unwrap_err()[0]
            assert isinstance(problem, errors.StateDirectoryUnavailable)
            assert problem.tool_name == self.name
            assert problem.path == (failure if isinstance(failure, Path) else None)
            assert problem.cause == (failure if isinstance(failure, Exception) else None)
        assert not list(tmp_path.iterdir())

    def test_native_access_failure_retains_cause(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.dict("os.environ", {"XDG_STATE_HOME": str(tmp_path / "state")})
        cause = PermissionError("denied")
        mocker.patch("llm_tool_cli.file_locks.files.FileLock", side_effect=cause)
        with project_lock(self.name, ProjectRootPath(tmp_path), timeout=0) as result:
            problem = result.unwrap_err()[0]
            assert isinstance(problem, lock_errors.AccessFailed)
            assert (
                problem.path
                == project_lock_path(
                    ToolStateDirectory.for_tool(self.name).unwrap(), ProjectRootPath(tmp_path)
                ).unwrap()
            )
            assert problem.cause == cause

    def test_rejects_symlinks_under_state_root(self, tmp_path: Path, mocker: MockerFixture) -> None:
        state = tmp_path / "state"
        mocker.patch.dict("os.environ", {"XDG_STATE_HOME": str(state)})
        (state / "sample").mkdir(parents=True)
        (state / "sample" / "projects").symlink_to(tmp_path, target_is_directory=True)
        with project_lock(self.name, ProjectRootPath(tmp_path), timeout=0) as result:
            assert isinstance(result.unwrap_err()[0], path_errors.InvalidProjectPath)
