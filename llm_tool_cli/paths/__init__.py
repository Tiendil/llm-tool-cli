"""Lexical identifiers, filesystem resolution, and project-root containment.

Lexical normalization is independent of the filesystem. Application-specific
syntax belongs to callers. ``paths.errors`` exposes public path failures.
"""

from llm_tool_cli.paths.filesystem import (
    ProjectRootPath,
    ResolvedProjectPath,
    resolve_inside_project,
    resolve_project_root,
)
from llm_tool_cli.paths.normalization import ProjectPathId, normalize_project_path_id

__all__ = [
    "ProjectPathId",
    "ProjectRootPath",
    "ResolvedProjectPath",
    "normalize_project_path_id",
    "resolve_inside_project",
    "resolve_project_root",
]
