from llm_tool_cli.protocol.output_cells.base import OutputCell, RenderContext


class LLMOutputCell(OutputCell):
    def render(self, context: RenderContext) -> bytes:  # noqa: CCR001
        id = self.short_id

        lines = [f"--{context.tool_label}-CELL {id} BEGIN--"]

        lines.append(f"kind={self.kind}")

        if self.media_type is not None:
            lines.append(f"media_type={self.media_type}")

        for meta_key, meta_value in sorted(self.meta.items()):
            lines.append(f"{meta_key}={meta_value}")

        if self.content:
            lines.append("")
            lines.append(self.content.strip())

        lines.append(f"--{context.tool_label}-CELL {id} END--")
        lines.append("")

        return "\n".join(lines).encode()
