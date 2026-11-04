from pathlib import Path

from llm_tool_cli.core import errors as core_errors


class EnvironmentError(core_errors.EnvironmentError):
    pass


class AccessFailed(EnvironmentError):
    code: str = "lock_access_failed"
    message: str = "Cannot acquire lock {error.path}: {error.reason}"
    ways_to_fix: list[str] = ["Ensure the lock's parent is writable and the coordination file is a regular file."]
    path: Path
    reason: str


class Timeout(EnvironmentError):
    code: str = "lock_timeout"
    message: str = "Timed out after {error.timeout} seconds waiting for {error.path}."
    ways_to_fix: list[str] = ["Wait for the operation holding this lock to finish, then retry."]
    path: Path
    timeout: float
