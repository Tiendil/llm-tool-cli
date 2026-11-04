from collections.abc import Iterator
from contextlib import contextmanager

from platformdirs import user_state_path

from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.file_locks import exclusive_lock
from llm_tool_cli.paths import (
    PathInput,
    ProjectRootPath,
    ResolvedProjectPath,
    resolve_inside_project,
    resolve_project_root,
)
from llm_tool_cli.paths.errors import InvalidProjectPath
from llm_tool_cli.tool_state import errors
from llm_tool_cli.tool_state.entities import StateRootPath


class ToolStateDirectory:
    """One resolved persistent state directory, shared across a tool's projects.

    Discovery and path selection create nothing. Named locks create their
    parents on acquisition and retain coordination files after release.
    """

    __slots__ = ("root",)

    def __init__(self, root: StateRootPath) -> None:
        self.root = root

    @classmethod
    @unwrap_to_error
    def for_tool(cls, name: ToolName) -> Result["ToolStateDirectory"]:
        """Discover the platform user-state location without a fallback."""
        try:
            location = user_state_path(name, appauthor=False, ensure_exists=False)
        except (OSError, RuntimeError) as exc:
            return Err([errors.StateDirectoryUnavailable(tool_name=name, reason=str(exc)).with_cause(exc)])
        if not location.is_absolute():
            return Err(
                [
                    errors.StateDirectoryUnavailable(
                        tool_name=name,
                        path=location,
                        reason="The user state directory must be absolute.",
                    )
                ]
            )
        root = resolve_project_root(location).unwrap()
        return Ok(cls(StateRootPath(root)))

    def resolve(self, relative_path: PathInput) -> Result[ResolvedProjectPath]:
        """Resolve a relative child, rejecting escapes and symlinks below the root."""
        if relative_path.is_absolute():
            return Err([InvalidProjectPath(path=str(relative_path))])
        return resolve_inside_project(self.root / relative_path, ProjectRootPath(self.root))

    @contextmanager
    def lock(self, relative_path: PathInput, *, timeout: float) -> Iterator[Result[None]]:
        """Hold a named exclusive lock; unrelated names coordinate independently."""
        selected = self.resolve(relative_path)
        if selected.is_err():
            yield Err(selected.unwrap_err())
            return
        with exclusive_lock(selected.unwrap(), timeout=timeout) as acquired:
            yield acquired
