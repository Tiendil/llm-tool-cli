"""Filesystem resolution and containment of project paths."""

from pathlib import Path
from typing import NewType

from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.paths.errors import InvalidProjectPath, PathResolutionFailed
from llm_tool_cli.paths.normalization import normalize_project_path_id

ProjectRootPath = NewType("ProjectRootPath", Path)
ResolvedProjectPath = NewType("ResolvedProjectPath", Path)


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


def resolve_inside_project(path: Path, root: ProjectRootPath) -> Result[ResolvedProjectPath]:
    """Resolve a filesystem path and require it to be strictly below the root.

    The root must already be resolved. Relative paths use the process working
    directory; callers choose any other base before calling. Do not expand
    home markers or require an existing target.
    """
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as error:
        return Err([PathResolutionFailed(path=str(path), reason=str(error)).with_cause(error)])

    if resolved == root or not resolved.is_relative_to(root):
        return Err([InvalidProjectPath(path=str(path))])

    return Ok(ResolvedProjectPath(resolved))


@unwrap_to_error
def resolve_root_anchored_path(value: str, root: ProjectRootPath) -> Result[ResolvedProjectPath]:
    """Normalize an ``@/`` identifier and resolve it strictly below the root.

    The root must already be resolved. Normalize identifier segments before
    resolving symlinks and checking containment, without requiring an existing
    target. Preserve lexical and filesystem resolution diagnostics.
    """
    normalized = normalize_project_path_id(value).unwrap()
    path = root.joinpath(*normalized.removeprefix("@/").split("/"))
    return resolve_inside_project(path, root)
