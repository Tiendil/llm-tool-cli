import shutil
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pydantic
import tomli
import tomli_w

from llm_tool_cli.core.errors import EnvironmentErrors
from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.file_locks import errors as lock_errors
from llm_tool_cli.file_locks import exclusive_lock
from llm_tool_cli.paths import PathSegment, ProjectRootPath, resolve_inside_project
from llm_tool_cli.tool_cache import errors
from llm_tool_cli.tool_cache.entities import CacheIdentity, CacheRootPath


def _write_identity(path: Path, identity: CacheIdentity) -> None:
    """Write a TOML ownership marker; the cache boundary handles filesystem failures."""
    with path.open("wb") as stream:
        tomli_w.dump(identity.model_dump(mode="json"), stream)


def _directories(path: Path) -> list[Path]:
    try:
        if not stat.S_ISDIR(path.lstat().st_mode):
            return []
    except FileNotFoundError:
        return []
    return [child for child in sorted(path.iterdir()) if stat.S_ISDIR(child.lstat().st_mode)]


def _owned_entry(entry: Path, namespace: str) -> bool:
    """Match a parsed identity to its namespace and digest; malformed markers remain unmanaged."""
    marker = entry / "identity.toml"
    try:
        if not stat.S_ISREG(marker.lstat().st_mode):
            return False
    except FileNotFoundError:
        return False

    try:
        identity = CacheIdentity.model_validate(tomli.loads(marker.read_text(encoding="utf-8")))
    except (UnicodeDecodeError, tomli.TOMLDecodeError, pydantic.ValidationError):
        # Until the marker and directory match, this may be unrelated data rather than owned state.
        return False
    return identity.namespace == namespace and entry.name == identity.digest


def _remove_entry(entry: Path) -> None:
    # Keep the ownership marker until payload removal succeeds so cleanup can be retried.
    for child in sorted(entry.iterdir()):
        if child.name == "identity.toml":
            continue
        if stat.S_ISDIR(child.lstat().st_mode):
            shutil.rmtree(child)
        else:
            child.unlink()
    (entry / "identity.toml").unlink()
    entry.rmdir()


class ToolCache:
    """Owned disposable entries under one resolved root and one persistent lock.

    Entries use ``<root>/<directory>/<namespace>/<identity-digest>``. The caller
    owns payloads and chooses the single-component directory and timeout policy.
    Construction performs no filesystem access.
    """

    __slots__ = ("root", "directory", "timeout")

    def __init__(self, *, root: CacheRootPath, directory: PathSegment, timeout: float) -> None:
        self.root = root
        self.directory = directory
        self.timeout = timeout

    def _lock_errors(self, problems: EnvironmentErrors) -> EnvironmentErrors:
        translated: EnvironmentErrors = []
        for problem in problems:
            reported: errors.AccessFailed
            if isinstance(problem, lock_errors.Timeout):
                reported = errors.LockTimeout(path=self.root, timeout=problem.timeout)
            elif isinstance(problem, lock_errors.AccessFailed):
                reported = errors.AccessFailed(path=self.root, reason=problem.reason)
            else:
                translated.append(problem)
                continue
            if problem.cause is not None:
                reported.with_cause(problem.cause)
            translated.append(reported)
        return translated

    def _prepare_root(self, *, create: bool) -> Result[bool]:
        try:
            if create:
                self.root.mkdir(parents=True, exist_ok=True)
            else:
                try:
                    mode = self.root.stat().st_mode
                except FileNotFoundError:
                    return Ok(False)
                if not stat.S_ISDIR(mode):
                    return Err([errors.AccessFailed(path=self.root, reason="Cache root must be a directory.")])
        except OSError as exc:
            return Err([errors.AccessFailed(path=self.root, reason=str(exc)).with_cause(exc)])
        return Ok(True)

    @contextmanager
    def _locked(self, *, create: bool) -> Iterator[Result[bool]]:
        prepared = self._prepare_root(create=create)
        if prepared.is_err() or not prepared.unwrap():
            yield prepared
            return
        path = resolve_inside_project(self.root / "cache.lock", ProjectRootPath(self.root))
        if path.is_err():
            yield Err(path.unwrap_err())
            return
        with exclusive_lock(path.unwrap(), timeout=self.timeout) as locked:
            yield Err(self._lock_errors(locked.unwrap_err())) if locked.is_err() else Ok(True)

    @contextmanager
    def entry(self, identity: CacheIdentity) -> Iterator[Result[Path]]:
        """Prepare an owned entry and hold exclusive cache access until the scope exits."""
        with self._locked(create=True) as access:
            if access.is_err():
                yield Err(access.unwrap_err())
            else:
                yield self._entry(identity)

    @unwrap_to_error
    def _entry(self, identity: CacheIdentity) -> Result[Path]:
        try:
            entry = resolve_inside_project(
                self.root / self.directory / identity.namespace / identity.digest, ProjectRootPath(self.root)
            ).unwrap()
            marker = entry / "identity.toml"
            if entry.exists():
                if not _owned_entry(entry, identity.namespace):
                    return Err([errors.AccessFailed(path=entry, reason="Conflicting cache ownership or identity.")])
            else:
                entry.mkdir(parents=True)
                _write_identity(marker, identity)
        except (OSError, UnicodeError) as exc:
            return Err([errors.AccessFailed(path=self.root, reason=str(exc)).with_cause(exc)])
        return Ok(entry)

    @unwrap_to_error
    def clean(self) -> Result[bool]:
        """Remove verified entries, preserving unrelated data, the root, and its lock.

        An absent root remains absent. Cleanup does not follow payload symlinks,
        retains ownership until deletion completes, and reports partial failure.
        """
        with self._locked(create=False) as access:
            if not access.unwrap():
                return Ok(False)
            try:
                entries = [
                    entry
                    for namespace in _directories(self.root / self.directory)
                    for entry in _directories(namespace)
                    if _owned_entry(entry, namespace.name)
                ]
            except OSError as exc:
                return Err([errors.AccessFailed(path=self.root, reason=str(exc)).with_cause(exc)])

            for entry in entries:
                try:
                    _remove_entry(entry)
                except OSError as exc:
                    return Err([errors.CleanupFailed(path=self.root, entry=entry, reason=str(exc)).with_cause(exc)])
            return Ok(bool(entries))
