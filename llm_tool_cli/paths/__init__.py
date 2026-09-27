"""Lexical identifiers, filesystem resolution, and project-root containment.

Lexical normalization is independent of the filesystem. Application-specific
syntax belongs to callers. ``paths.errors`` exposes public path failures.
"""

from llm_tool_cli.paths.filesystem import (
    ProjectRootPath,
    ResolvedProjectPath,
    normalize_path,
    project_path_id_from_filesystem,
    project_path_id_from_resolved,
    resolve_inside_project,
    resolve_project_root,
    resolve_root_anchored_path,
)
from llm_tool_cli.paths.normalization import ProjectPathId, normalize_project_path_id

__all__ = [
    "ProjectPathId",
    "ProjectRootPath",
    "ResolvedProjectPath",
    "normalize_path",
    "normalize_project_path_id",
    "project_path_id_from_filesystem",
    "project_path_id_from_resolved",
    "resolve_inside_project",
    "resolve_project_root",
    "resolve_root_anchored_path",
]
