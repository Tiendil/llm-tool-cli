"""Deterministic project-file discovery without symlink traversal."""

import fnmatch
import glob
import os.path
import stat
from collections.abc import Iterator
from pathlib import Path
from typing import NewType

from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.paths.errors import FilesUnreadable, InvalidProjectPath, PathResolutionFailed
from llm_tool_cli.paths.filesystem import (
    ProjectRootPath,
    ResolvedProjectPath,
    _project_path_input,
    _validate_no_symlinks,
    project_path_id_from_resolved,
    resolve_project_root,
)
from llm_tool_cli.paths.normalization import ProjectPathId

FileGlobPattern = NewType("FileGlobPattern", str)
"""A supplied filesystem glob without validity or containment guarantees."""


@unwrap_to_error
def _pattern_parts(pattern: FileGlobPattern, root: ProjectRootPath) -> Result[tuple[str, ...]]:
    """Resolve the literal prefix without treating glob syntax as filenames."""
    candidate = _project_path_input(pattern, root).unwrap()
    parts = candidate.parts
    start = len(root.parts) if candidate.is_relative_to(root) else 0
    first_magic = next((index for index in range(start, len(parts)) if glob.has_magic(parts[index])), len(parts))
    prefix = Path(*parts[:first_magic])
    try:
        _validate_no_symlinks(prefix, root).unwrap()
        resolved = prefix.resolve().joinpath(*parts[first_magic:])
    except (OSError, RuntimeError) as error:
        return Err([PathResolutionFailed(path=str(candidate), reason=str(error)).with_cause(error)])
    normalized = Path(os.path.normpath(resolved))
    if normalized == root or not normalized.is_relative_to(root):
        return Err([InvalidProjectPath(path=str(candidate))])
    return Ok(normalized.relative_to(root).parts)


def _glob_files(path: Path, parts: tuple[str, ...]) -> Iterator[Path]:  # noqa: CCR001
    try:
        mode = path.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return

    if not parts or stat.S_ISREG(mode):
        if stat.S_ISREG(mode) and all(part == "**" for part in parts):
            yield path
        return
    if not stat.S_ISDIR(mode):
        return

    segment, *remaining = parts
    if segment == "**":
        yield from _glob_files(path, tuple(remaining))
    for entry in sorted(path.iterdir()):
        if segment == "**":
            yield from _glob_files(entry, parts)
        elif fnmatch.fnmatchcase(entry.name, segment):
            yield from _glob_files(entry, tuple(remaining))


@unwrap_to_error
def enumerate_files(root: Path, pattern: FileGlobPattern = FileGlobPattern("**/*")) -> Result[list[ProjectPathId]]:
    """Find regular files matching a project-relative or root-anchored glob.

    Support absolute and home-relative patterns through shared path resolution.
    Include hidden entries, skip all discovered symlinks, and reject symlinks
    in explicit pattern components. Return unique ids in path-component order.
    """
    project_root = resolve_project_root(root).unwrap()
    parts = _pattern_parts(pattern, project_root).unwrap()
    try:
        paths = sorted(set(_glob_files(project_root, parts)))
    except OSError as error:
        return Err([FilesUnreadable(path=str(project_root), reason=str(error)).with_cause(error)])
    return Ok([project_path_id_from_resolved(ResolvedProjectPath(path), project_root) for path in paths])
