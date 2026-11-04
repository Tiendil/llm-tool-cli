from pathlib import Path

from llm_tool_cli.core import errors as core_errors


class EnvironmentError(core_errors.EnvironmentError):
    pass


class AccessFailed(EnvironmentError):
    code: str = "cache_access_failed"
    message: str = "Cannot access cache {error.path}: {error.reason}"
    ways_to_fix: list[str] = ["Select a usable cache directory."]
    path: Path
    reason: str


class LockTimeout(AccessFailed):
    code: str = "cache_lock_timeout"
    message: str = "Cache {error.path} is busy: timed out after {error.timeout} seconds waiting for cache.lock."
    reason: str = "Timed out waiting for cache.lock."
    ways_to_fix: list[str] = [
        "Wait for the operation using this cache to finish, then retry.",
        "Select a separate cache directory if the other operation must continue.",
    ]
    timeout: float


class CleanupFailed(AccessFailed):
    code: str = "cache_cleanup_failed"
    message: str = (
        "Cannot finish cleaning cache {error.path} at {error.entry}: {error.reason}. "
        "Cached data may already have been partially removed."
    )
    ways_to_fix: list[str] = ["Resolve the reported filesystem failure and retry cache cleanup."]
    entry: Path
