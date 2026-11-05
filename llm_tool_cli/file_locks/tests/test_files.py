from pathlib import Path

import pytest
from filelock import FileLock, Timeout
from pytest_mock import MockerFixture

from llm_tool_cli.file_locks import errors, exclusive_lock
from llm_tool_cli.file_locks.tests.helpers import held_lock
from llm_tool_cli.paths import ResolvedProjectPath


class TestExclusiveLock:
    def test_creates_parents_and_preserves_file_identity(self, tmp_path: Path) -> None:
        path = ResolvedProjectPath(tmp_path / "state" / "operation.lock")
        scope = exclusive_lock(path, timeout=0)
        assert not path.parent.exists()
        with scope as result:
            result.unwrap()
            inode = path.stat().st_ino
            with pytest.raises(Timeout), FileLock(path, timeout=0, preserve_lock_file=True):
                pass
        with exclusive_lock(path, timeout=0) as result:
            result.unwrap()
            assert path.stat().st_ino == inode

    def test_nested_scopes_hold_until_outer_release(self, tmp_path: Path) -> None:
        path = ResolvedProjectPath(tmp_path / "operation.lock")
        with exclusive_lock(path, timeout=0) as outer:
            outer.unwrap()
            with exclusive_lock(path, timeout=0.1) as inner:
                inner.unwrap()
            with pytest.raises(Timeout), FileLock(path, timeout=0, preserve_lock_file=True):
                pass
        with FileLock(path, timeout=0, preserve_lock_file=True):
            pass

    def test_body_exception_releases_lock(self, tmp_path: Path) -> None:
        path = ResolvedProjectPath(tmp_path / "operation.lock")
        with pytest.raises(ValueError, match="body failed"):
            with exclusive_lock(path, timeout=0) as result:
                result.unwrap()
                raise ValueError("body failed")
        with FileLock(path, timeout=0, preserve_lock_file=True):
            pass

    def test_timeout_and_process_termination(self, tmp_path: Path) -> None:
        path = ResolvedProjectPath(tmp_path / "operation.lock")
        with held_lock(path) as process:
            with exclusive_lock(path, timeout=0) as blocked:
                problem = blocked.unwrap_err()[0]
                assert isinstance(problem, errors.Timeout)
                assert problem.path == path
                assert problem.timeout == 0
                assert isinstance(problem.cause, Timeout)
            inode = path.stat().st_ino
            process.kill()
            process.wait(timeout=5)
        with exclusive_lock(path, timeout=0) as acquired:
            acquired.unwrap()
        assert path.stat().st_ino == inode

    @pytest.mark.parametrize("kind", ["directory", "symlink"])
    def test_nonregular_file_is_preserved(self, tmp_path: Path, kind: str) -> None:
        path = ResolvedProjectPath(tmp_path / "operation.lock")
        if kind == "directory":
            path.mkdir()
        else:
            target = tmp_path / "target"
            target.write_text("unrelated")
            path.symlink_to(target)
        with exclusive_lock(path, timeout=0) as result:
            problem = result.unwrap_err()[0]
            assert isinstance(problem, errors.AccessFailed)
            assert problem.path == path
        assert path.is_symlink() if kind == "symlink" else path.is_dir()

    def test_parent_failure_retains_cause(self, tmp_path: Path) -> None:
        parent = tmp_path / "parent"
        parent.write_text("unrelated")
        with exclusive_lock(ResolvedProjectPath(parent / "operation.lock"), timeout=0) as result:
            problem = result.unwrap_err()[0]
            assert isinstance(problem, errors.AccessFailed)
            assert isinstance(problem.cause, OSError)
        assert parent.read_text() == "unrelated"

    def test_native_failure_is_reported(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cause = PermissionError("denied")
        mocker.patch("llm_tool_cli.file_locks.files.FileLock", side_effect=cause)
        with exclusive_lock(ResolvedProjectPath(tmp_path / "operation.lock"), timeout=0) as result:
            problem = result.unwrap_err()[0]
            assert isinstance(problem, errors.AccessFailed)
            assert problem.cause == cause

    def test_unexpected_failure_propagates(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cause = RuntimeError("unexpected")
        mocker.patch("llm_tool_cli.file_locks.files.FileLock", side_effect=cause)
        with pytest.raises(RuntimeError, match="unexpected"):
            with exclusive_lock(ResolvedProjectPath(tmp_path / "operation.lock"), timeout=0):
                pytest.fail("Unexpected acquisition failures must propagate")
