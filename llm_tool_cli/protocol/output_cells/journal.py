import pydantic

from llm_tool_cli.protocol.output_cells.base import OutputCell, RenderContext
from llm_tool_cli.protocol.serialization import to_jsonl


class JournalTextOutputCell(OutputCell):
    """Compact journal presentation without changing the logical message."""

    model_config = pydantic.ConfigDict(str_strip_whitespace=False)

    def render(self, context: RenderContext) -> bytes:
        text = (self.content or "").replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")
        return (text + "\n").encode("utf-8")


class JournalAutomationOutputCell(OutputCell):
    """One structured journal record with its original field values."""

    model_config = pydantic.ConfigDict(str_strip_whitespace=False)

    def render(self, context: RenderContext) -> bytes:
        return to_jsonl(self.meta).encode("utf-8")
