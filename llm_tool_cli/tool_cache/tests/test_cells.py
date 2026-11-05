from pathlib import Path

import pytest

from llm_tool_cli.paths import CacheRootPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.tool_cache.cells import CacheCleanCell


class TestCacheCleanCell:
    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize(("changed", "outcome"), [(True, "cleaned"), (False, "unchanged")])
    def test_render__projects_cleanup_result(self, protocol: Protocol, changed: bool, outcome: str) -> None:
        cell = CacheCleanCell(cache_dir=CacheRootPath(Path("/cache")), changed=changed)
        projected = cell.render(protocol)
        assert len(projected) == 1
        assert projected[0].content is None
        assert projected[0].meta == {
            "type": "cache",
            "operation": "clean",
            "cache_dir": "/cache",
            "outcome": outcome,
        }
