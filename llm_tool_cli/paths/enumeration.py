"""Deterministic project-file discovery without symlink traversal."""

import stat
from collections.abc import Iterator
from pathlib import Path

from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.paths.errors import FilesUnreadable
from llm_tool_cli.paths.filesystem import (
    ResolvedProjectPath,
    project_path_id_from_resolved,
    resolve_project_root,
)
from llm_tool_cli.paths.globs import FileGlobPattern, _compile_glob, _pattern_parts
from llm_tool_cli.paths.normalization import ProjectPathId


def _glob_files(path: Path, parts: tuple[str, ...]) -> Iterator[Path]:  # noqa: CCR001
    try:
        mode = path.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return

    if not parts:
        if stat.S_ISREG(mode):
            yield path
        return
    if not stat.S_ISDIR(mode):
        return

    segment, *remaining = parts
    compiled, recursive = _compile_glob(FileGlobPattern(segment)).unwrap()
    if recursive:
        compiled, _ = _compile_glob(FileGlobPattern("/".join(parts))).unwrap()
        for entry in _walk_files(path):
            if compiled.fullmatch(entry.relative_to(path).as_posix()):
                yield entry
        return
    for entry in sorted(path.iterdir()):
        if compiled.fullmatch(entry.name):
            yield from _glob_files(entry, tuple(remaining))


def _walk_files(path: Path) -> Iterator[Path]:
    """Walk regular files without following links, including broken links."""
    try:
        mode = path.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return
    if stat.S_ISREG(mode):
        yield path
    elif stat.S_ISDIR(mode):
        for entry in sorted(path.iterdir()):
            yield from _walk_files(entry)


@unwrap_to_error
def enumerate_files(root: Path, pattern: FileGlobPattern = FileGlobPattern("**/*")) -> Result[list[ProjectPathId]]:
    """Find regular files matching a project-relative or root-anchored glob.

    Support absolute and home-relative patterns through shared path resolution.
    Include hidden entries, skip all discovered symlinks, and reject symlinks
    in explicit pattern components. Return unique ids in path-component order.
    """
    project_root = resolve_project_root(root).unwrap()
    parts = _pattern_parts(pattern, project_root).unwrap()
    _compile_glob(FileGlobPattern("/".join(parts))).unwrap()
    try:
        paths = sorted(set(_glob_files(project_root, parts)))
    except OSError as error:
        return Err([FilesUnreadable(path=str(project_root), reason=str(error)).with_cause(error)])
    return Ok([project_path_id_from_resolved(ResolvedProjectPath(path), project_root) for path in paths])
