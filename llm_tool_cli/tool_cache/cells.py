"""Pure result projections for shared cache operations."""

from llm_tool_cli.paths import CacheRootPath
from llm_tool_cli.protocol.logic_cells.uniform import UniformCell
from llm_tool_cli.protocol.output_cells.base import OutputCell


class CacheCleanCell(UniformCell):
    cache_dir: CacheRootPath
    changed: bool

    def _render(self, cell_type: type[OutputCell]) -> OutputCell:
        return cell_type.build_meta(
            "cache",
            type="cache",
            operation="clean",
            cache_dir=str(self.cache_dir),
            outcome="cleaned" if self.changed else "unchanged",
        )
