"""Application settings bound before command-line parsing in the active context."""

from typing import NewType

from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.core.errors import ToolLabelAlreadyInitialized

ToolLabel = NewType("ToolLabel", str)

tool_label = ContextValue[ToolLabel]("tool_label")


def initialize(*, label: ToolLabel) -> None:
    if tool_label.is_set():
        current = tool_label.get()
        if current != label:
            raise ToolLabelAlreadyInitialized(details={"current": current, "requested": label})
        return

    tool_label.initialize(label)
