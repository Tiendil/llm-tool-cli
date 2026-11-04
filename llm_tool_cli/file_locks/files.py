import stat
from collections.abc import Iterator
from contextlib import contextmanager

from filelock import BaseFileLock, FileLock, Timeout

from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.file_locks import errors
from llm_tool_cli.paths import ResolvedProjectPath


def _acquire(path: ResolvedProjectPath, *, timeout: float) -> Result[BaseFileLock]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            mode = None
        if mode is not None and not stat.S_ISREG(mode):
            return Err([errors.AccessFailed(path=path, reason="The coordination file must be a regular file.")])

        lock = FileLock(path, preserve_lock_file=True, fallback_to_soft=False, is_singleton=True)
        lock.acquire(timeout=timeout)
    except Timeout as exc:
        return Err([errors.Timeout(path=path, timeout=timeout).with_cause(exc)])
    except OSError as exc:
        return Err([errors.AccessFailed(path=path, reason=str(exc)).with_cause(exc)])
    return Ok(lock)


@contextmanager
def exclusive_lock(path: ResolvedProjectPath, *, timeout: float) -> Iterator[Result[None]]:
    """Hold a native exclusive lock, retaining its file after release.

    The caller supplies a resolved, contained path and owns timeout policy.
    Missing parent directories are created on entry. Nested scopes in the same
    thread retain the lock until their outermost scope exits. Expected acquisition
    failures yield diagnostics; body exceptions propagate after release.
    """
    acquired = _acquire(path, timeout=timeout)
    if acquired.is_err():
        yield Err(acquired.unwrap_err())
        return

    lock = acquired.unwrap()
    try:
        yield Ok(None)
    finally:
        lock.release()
