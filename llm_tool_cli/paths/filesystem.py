"""Filesystem resolution and containment of project paths."""

import stat
from pathlib import Path
from typing import NewType

from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.paths.errors import InvalidProjectPath, PathResolutionFailed
from llm_tool_cli.paths.normalization import ProjectPathId, normalize_project_path_id, project_path_parts

PathInput = NewType("PathInput", Path)
ProjectConfigPath = NewType("ProjectConfigPath", Path)
ProjectRootPath = NewType("ProjectRootPath", Path)
RelativeProjectPath = NewType("RelativeProjectPath", Path)
ResolvedProjectPath = NewType("ResolvedProjectPath", Path)


@unwrap_to_error
def _project_path_input(value: str, root: ProjectRootPath, *, allow_absolute: bool = True) -> Result[PathInput]:
    """Select a filesystem candidate without interpreting its target."""
    if not value:
        return Err([InvalidProjectPath(path=value)])
    if value.startswith("@"):
        normalized = normalize_project_path_id(value).unwrap()
        return Ok(PathInput(root.joinpath(*project_path_parts(normalized))))

    try:
        path = Path(value).expanduser()
    except (OSError, RuntimeError) as error:
        return Err([PathResolutionFailed(path=value, reason=str(error)).with_cause(error)])

    if path.is_absolute() and not allow_absolute:
        return Err([InvalidProjectPath(path=value)])

    return Ok(PathInput(path if path.is_absolute() else root / path))


@unwrap_to_error
def resolve_project_path(value: str, root: Path, *, allow_absolute: bool = True) -> Result[ResolvedProjectPath]:
    """Resolve an identifier or filesystem input at or below a project root.

    Resolve the root first. Normalize identifiers before checking for symlinks;
    expand home markers only in filesystem inputs. Relative filesystem inputs
    use the resolved root. When absolute inputs are disabled, reject paths
    that are absolute after home expansion. Do not require an existing target.
    """
    project_root = resolve_project_root(root).unwrap()
    candidate = _project_path_input(value, project_root, allow_absolute=allow_absolute).unwrap()
    return resolve_inside_project(candidate, project_root)


@unwrap_to_error
def normalize_path(value: str, root: Path, *, cwd: Path | None = None) -> Result[ProjectPathId]:
    """Normalize an identifier or filesystem input to a project identifier.

    Resolve the root first and reject empty inputs. Normalize inputs starting
    with ``@`` lexically; otherwise expand home markers. Enforce containment
    and reject symlinks below the root in both cases. Relative inputs use the
    supplied directory base, or the resolved root.
    Neither form requires an existing target.
    """
    project_root = resolve_project_root(root).unwrap()

    if not value:
        return Err([InvalidProjectPath(path=value)])

    if value.startswith("@"):
        resolved = resolve_root_anchored_path(value, project_root).unwrap()
        return Ok(project_path_id_from_resolved(resolved, project_root))

    try:
        path = Path(value).expanduser()
    except (OSError, RuntimeError) as error:
        return Err([PathResolutionFailed(path=value, reason=str(error)).with_cause(error)])

    candidate = path if path.is_absolute() else (cwd if cwd is not None else project_root) / path
    resolved = resolve_inside_project(candidate, project_root).unwrap()
    return Ok(project_path_id_from_resolved(resolved, project_root))


@unwrap_to_error
def project_path_id_from_filesystem(path: Path, root: Path) -> Result[ProjectPathId]:
    """Resolve a filesystem path and convert it to a project identifier.

    Resolve the supplied root first, then enforce containment at or below it.
    Relative roots and paths use the process working directory. Do not expand
    home markers, interpret identifiers, or require an existing target.
    Preserve root and target resolution failures and containment diagnostics.
    """
    project_root = resolve_project_root(root).unwrap()
    resolved = resolve_inside_project(path, project_root).unwrap()
    return Ok(project_path_id_from_resolved(resolved, project_root))


def project_path_id_from_resolved(path: ResolvedProjectPath, root: ProjectRootPath) -> ProjectPathId:
    """Convert a resolved path at or below its resolved root to an identifier.

    The path must already have passed containment resolution for this root.
    Preserve segment text without filesystem access or repeated validation.
    """
    return ProjectPathId("@/" + "/".join(path.relative_to(root).parts))


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


def _validate_no_symlinks(path: Path, root: ProjectRootPath) -> Result[None]:  # noqa: CCR001
    """Reject links below the resolved root before resolving the target."""
    candidate = path.absolute()
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current = current.parent if part == ".." else current / part
        if current == root or not current.is_relative_to(root):
            # Root aliases and symlinks above the chosen root remain supported.
            current = current.resolve()
            continue
        try:
            mode = current.lstat().st_mode
        except (FileNotFoundError, NotADirectoryError):
            continue
        if stat.S_ISLNK(mode):
            return Err([InvalidProjectPath(path=str(path))])
    return Ok(None)


@unwrap_to_error
def resolve_inside_project(path: Path, root: ProjectRootPath) -> Result[ResolvedProjectPath]:
    """Resolve a filesystem path and require it to be at or below the root.

    The root must already be resolved. Relative paths use the process working
    directory; callers choose any other base before calling. Do not expand
    home markers or require an existing target.
    """
    try:
        _validate_no_symlinks(path, root).unwrap()
        resolved = path.resolve()
    except (OSError, RuntimeError) as error:
        return Err([PathResolutionFailed(path=str(path), reason=str(error)).with_cause(error)])

    if not resolved.is_relative_to(root):
        return Err([InvalidProjectPath(path=str(path))])

    return Ok(ResolvedProjectPath(resolved))


@unwrap_to_error
def resolve_root_anchored_path(value: str, root: ProjectRootPath) -> Result[ResolvedProjectPath]:
    """Normalize an ``@/`` identifier and resolve it at or below the root.

    The root must already be resolved. Normalize identifier segments before
    resolving symlinks and checking containment, without requiring an existing
    target. Preserve lexical and filesystem resolution diagnostics.
    """
    normalized = normalize_project_path_id(value).unwrap()
    path = root.joinpath(*project_path_parts(normalized))
    return resolve_inside_project(path, root)
