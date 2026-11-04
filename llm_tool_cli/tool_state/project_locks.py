"""Project operation coordination built on generic tool-state directories."""

import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.core.result import Err, Result
from llm_tool_cli.paths import PathInput, ProjectRootPath, ResolvedProjectPath
from llm_tool_cli.tool_state.directory import ToolStateDirectory


def _relative_lock_path(project_root: ProjectRootPath) -> PathInput:
    identity = hashlib.sha256(os.fsencode(os.path.normcase(str(project_root)))).hexdigest()
    return PathInput(Path("projects") / identity / "operation.lock")


def project_lock_path(state: ToolStateDirectory, project_root: ProjectRootPath) -> Result[ResolvedProjectPath]:
    """Select a stable lock for an already resolved project root, without creating it."""
    return state.resolve(_relative_lock_path(project_root))


@contextmanager
def project_lock(name: ToolName, project_root: ProjectRootPath, *, timeout: float) -> Iterator[Result[None]]:
    """Discover state and hold a project's lock, propagating failures unchanged.

    Configuration filenames and cache locations do not affect identity. The
    caller owns root selection and scope lifetime; no project is loaded here.
    """
    selected = ToolStateDirectory.for_tool(name)
    if selected.is_err():
        yield Err(selected.unwrap_err())
        return
    with selected.unwrap().lock(_relative_lock_path(project_root), timeout=timeout) as acquired:
        yield acquired
