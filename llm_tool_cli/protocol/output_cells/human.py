from llm_tool_cli.protocol.output_cells.base import OutputCell, RenderContext


class HumanOutputCell(OutputCell):
    def render(self, context: RenderContext) -> bytes:
        sections = [self._render_metadata(), (self.content or "").strip()]
        text = "\n\n".join(section for section in sections if section) or self.kind
        return (text + "\n\n").encode("utf-8")

    def _render_metadata(self) -> str:
        return "\n".join(
            f"{key}: {value}" for key, value in sorted(self.meta.items()) if not (key == "type" and value == self.kind)
        )


class HumanErrorOutputCell(HumanOutputCell):
    def render(self, context: RenderContext) -> bytes:
        sections = [f"Error: {(self.content or '').strip()}".rstrip(), self._render_metadata()]
        return ("\n\n".join(section for section in sections if section) + "\n\n").encode("utf-8")


class HumanWarningOutputCell(HumanOutputCell):
    def render(self, context: RenderContext) -> bytes:
        return (f"Warning: {self.meta['message']}".rstrip() + "\n\n").encode("utf-8")
