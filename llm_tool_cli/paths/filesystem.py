"""Filesystem resolution of project roots."""

from pathlib import Path
from typing import NewType

from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.paths.errors import PathResolutionFailed

ProjectRootPath = NewType("ProjectRootPath", Path)


def resolve_project_root(root: Path) -> Result[ProjectRootPath]:
    """Resolve a filesystem root without requiring an existing directory.

    Relative roots use the process working directory. Resolve symlinks and
    parent segments without expanding home markers. Return filesystem
    resolution failures with their original cause.
    """
    try:
        return Ok(ProjectRootPath(root.resolve()))
    except (OSError, RuntimeError) as error:
        return Err([PathResolutionFailed(path=str(root), reason=str(error)).with_cause(error)])
