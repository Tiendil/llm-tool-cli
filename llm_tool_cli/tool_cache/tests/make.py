from pathlib import Path

from llm_tool_cli.paths import CacheRootPath, PathSegment
from llm_tool_cli.tool_cache import ToolCache


def cache_storage(root: Path) -> ToolCache:
    return ToolCache(root=CacheRootPath(root), directory=PathSegment("entries"), timeout=0.05)
