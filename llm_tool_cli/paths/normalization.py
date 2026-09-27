"""Lexical normalization of project-path identifiers."""

from typing import NewType

from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.paths.errors import InvalidProjectPath

ProjectPathId = NewType("ProjectPathId", str)

_PROJECT_ROOT_PREFIX = "@/"


def normalize_project_path_id(value: str) -> Result[ProjectPathId]:
    """Normalize a root-anchored identifier without accessing the filesystem.

    Remove ``.`` and resolve ``..`` lexically. Reject missing ``@/``, empty
    segments, traversal above the root, and a final root-only identifier with
    ``Err([InvalidProjectPath(...)])``. Preserve all other segment text.
    """
    if not value.startswith(_PROJECT_ROOT_PREFIX):
        return Err([InvalidProjectPath(path=value)])

    parts: list[str] = []
    for part in value.removeprefix(_PROJECT_ROOT_PREFIX).split("/"):
        match part:
            case "":
                return Err([InvalidProjectPath(path=value)])
            case ".":
                continue
            case "..":
                if not parts:
                    return Err([InvalidProjectPath(path=value)])
                parts.pop()
            case _:
                parts.append(part)

    if not parts:
        return Err([InvalidProjectPath(path=value)])

    return Ok(ProjectPathId(_PROJECT_ROOT_PREFIX + "/".join(parts)))


def is_project_path_id(value: object) -> bool:
    """Check whether an input is already a canonical project-path identifier.

    Return false for non-strings and values requiring lexical normalization.
    Do not access the filesystem or apply application-specific rules.
    """
    return isinstance(value, str) and normalize_project_path_id(value).ok() == value
