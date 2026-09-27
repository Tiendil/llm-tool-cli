"""Lexical project-path identifiers, independent of the filesystem.

``ProjectPathId``, ``normalize_project_path_id``, and ``paths.errors`` are public.
Filesystem resolution, containment, and application-specific syntax belong to callers.
"""

from llm_tool_cli.paths.normalization import ProjectPathId, normalize_project_path_id

__all__ = ["ProjectPathId", "normalize_project_path_id"]
