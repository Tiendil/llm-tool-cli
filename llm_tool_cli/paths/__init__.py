"""Lexical project-path identifiers and filesystem project-root resolution.

Lexical normalization is independent of the filesystem. Project-path
containment and application-specific syntax belong to callers.
``paths.errors`` exposes public failures for both operations.
"""

from llm_tool_cli.paths.filesystem import ProjectRootPath, resolve_project_root
from llm_tool_cli.paths.normalization import ProjectPathId, normalize_project_path_id

__all__ = ["ProjectPathId", "ProjectRootPath", "normalize_project_path_id", "resolve_project_root"]
