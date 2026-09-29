from llm_tool_cli.protocol import to_jsonl
from llm_tool_cli.protocol.output_cells.base import MetaValue, OutputCell, RenderContext


class AutomationOutputCell(OutputCell):
    def render(self, context: RenderContext) -> bytes:
        data: dict[str, MetaValue] = {"id": self.short_id}

        for meta_key, meta_value in sorted(self.meta.items()):
            data[meta_key] = meta_value

        data["content"] = self.content.strip() if self.content else None

        return to_jsonl(data).encode("utf-8")
