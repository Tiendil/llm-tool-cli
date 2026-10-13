"""Shared project glob preparation, matching, and named captures."""

import fnmatch
import glob
import os.path
import re
from pathlib import Path
from typing import NewType

from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.paths.errors import InvalidGlobPattern, InvalidProjectPath, PathResolutionFailed
from llm_tool_cli.paths.filesystem import (
    ProjectRootPath,
    _project_path_input,
    _validate_no_symlinks,
    resolve_project_root,
)
from llm_tool_cli.paths.normalization import ProjectPathId, project_path_parts

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


def _compile_glob(pattern: FileGlobPattern) -> Result[tuple[re.Pattern[str], bool]]:  # noqa: CCR001, TAE002
    """Compile path syntax and report whether it can cross directory boundaries."""
    regex: list[str] = []
    recursive = False
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "[":
            end = index + 1
            if end < len(pattern) and pattern[end] == "!":
                end += 1
            if end < len(pattern) and pattern[end] == "]":
                end += 1
            end = pattern.find("]", end)
            if end != -1 and "/" not in pattern[index : end + 1]:
                # Delegate character-class rules (including escaping and invalid
                # ranges) to fnmatch, removing its whole-string wrapper.
                translated = fnmatch.translate(pattern[index : end + 1])
                regex.append("(?!/)" + translated[4:-3])
                index = end + 1
                continue

        if character == "{" and pattern[index + 1 : index + 2] == "*":
            end = pattern.find("}", index)
            if end == -1:
                return Err([InvalidGlobPattern(pattern=pattern, reason="unclosed capture")])
            token = pattern[index + 1 : end]
            wildcard = "**" if token.startswith("**") else "*"
            name = token[len(wildcard) :]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
                return Err([InvalidGlobPattern(pattern=pattern, reason=f"invalid capture name `{name}`")])
            index = end + 1
            if wildcard == "**":
                recursive = True
                if pattern[index : index + 1] == "/":
                    regex.append(f"(?:(?P<{name}>.*)/)?")
                    index += 1
                else:
                    regex.append(f"(?P<{name}>.*)")
            else:
                regex.append(f"(?P<{name}>[^/]*)")
            continue

        if pattern[index : index + 2] == "**":
            recursive = True
            index += 2
            if pattern[index : index + 1] == "/":
                regex.append("(?:.*/)?")
                index += 1
            else:
                regex.append(".*")
            continue

        regex.append("[^/]*" if character == "*" else "[^/]" if character == "?" else re.escape(character))
        index += 1

    try:
        return Ok((re.compile("".join(regex), re.DOTALL), recursive))
    except re.error as error:
        return Err([InvalidGlobPattern(pattern=pattern, reason=str(error)).with_cause(error)])


@unwrap_to_error
def glob_capture_names(pattern: FileGlobPattern) -> Result[set[str]]:
    """Validate glob syntax and collect capture names without filesystem access."""
    compiled, _ = _compile_glob(pattern).unwrap()
    return Ok(set(compiled.groupindex))


@unwrap_to_error
def match_glob(path: ProjectPathId, pattern: FileGlobPattern, root: Path) -> Result[dict[str, str] | None]:
    """Match an already normalized identifier, including a missing reference.

    Only the pattern's literal prefix is resolved against the filesystem.
    Return captured strings (empty for omitted recursive directories), an empty
    dictionary for a match without captures, or None for a non-match.
    """
    project_root = resolve_project_root(root).unwrap()
    parts = _pattern_parts(pattern, project_root).unwrap()
    compiled, _ = _compile_glob(FileGlobPattern("/".join(parts))).unwrap()
    match = compiled.fullmatch("/".join(project_path_parts(path)))
    return Ok({name: value or "" for name, value in match.groupdict().items()} if match else None)
