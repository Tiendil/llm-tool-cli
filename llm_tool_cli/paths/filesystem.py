"""Filesystem resolution and containment of project paths."""

from pathlib import Path
from typing import NewType

from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.paths.errors import InvalidProjectPath, PathResolutionFailed
from llm_tool_cli.paths.normalization import ProjectPathId, normalize_project_path_id, project_path_parts

ProjectRootPath = NewType("ProjectRootPath", Path)
ResolvedProjectPath = NewType("ResolvedProjectPath", Path)
UntrustedPath = NewType("UntrustedPath", Path)


@unwrap_to_error
def resolve_project_path(value: str, root: Path, *, allow_absolute: bool = True) -> Result[ResolvedProjectPath]:
    """Resolve an identifier or filesystem input strictly below a project root.

    Resolve the root first. Normalize identifiers before resolving symlinks;
    expand home markers only in filesystem inputs. Relative filesystem inputs
    use the resolved root. When absolute inputs are disabled, reject paths
    that are absolute after home expansion. Do not require an existing target.
    """
    project_root = resolve_project_root(root).unwrap()

    if value.startswith("@"):
        return resolve_root_anchored_path(value, project_root)

    try:
        path = Path(value).expanduser()
    except (OSError, RuntimeError) as error:
        return Err([PathResolutionFailed(path=value, reason=str(error)).with_cause(error)])

    if path.is_absolute() and not allow_absolute:
        return Err([InvalidProjectPath(path=value)])

    candidate = path if path.is_absolute() else project_root / path
    return resolve_inside_project(candidate, project_root)


@unwrap_to_error
def normalize_path(value: str, root: Path, *, cwd: Path | None = None) -> Result[ProjectPathId]:
    """Normalize an identifier or filesystem input to a project identifier.

    Resolve the root first and reject empty inputs. Normalize inputs starting
    with ``@`` lexically; otherwise expand home markers and enforce filesystem
    containment. Relative inputs use the supplied directory base, or the resolved root.
    Neither form requires an existing target.
    """
    project_root = resolve_project_root(root).unwrap()

    if not value:
        return Err([InvalidProjectPath(path=value)])

    if value.startswith("@"):
        return normalize_project_path_id(value)

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

    Resolve the supplied root first, then enforce containment strictly below it.
    Relative roots and paths use the process working directory. Do not expand
    home markers, interpret identifiers, or require an existing target.
    Preserve root and target resolution failures and containment diagnostics.
    """
    project_root = resolve_project_root(root).unwrap()
    resolved = resolve_inside_project(path, project_root).unwrap()
    return Ok(project_path_id_from_resolved(resolved, project_root))


def project_path_id_from_resolved(path: ResolvedProjectPath, root: ProjectRootPath) -> ProjectPathId:
    """Convert a resolved path strictly below its resolved root to an identifier.

    The path must already have passed containment resolution for this root.
    Preserve segment text without filesystem access or repeated validation.
    """
    return ProjectPathId("@/" + path.relative_to(root).as_posix())


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
    path = root.joinpath(*project_path_parts(normalized))
    return resolve_inside_project(path, root)
