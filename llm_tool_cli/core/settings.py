"""Process-wide application settings, initialized before command-line parsing."""

from typing import NewType

from llm_tool_cli.core.errors import ToolLabelAlreadyInitialized, ToolLabelNotInitialized

ToolLabel = NewType("ToolLabel", str)

_tool_label: ToolLabel | None = None


def initialize(*, tool_label: ToolLabel) -> None:
    global _tool_label

    if _tool_label is not None and _tool_label != tool_label:
        raise ToolLabelAlreadyInitialized(details={"current": _tool_label, "requested": tool_label})

    _tool_label = tool_label


def get_tool_label() -> ToolLabel:
    if _tool_label is None:
        raise ToolLabelNotInitialized()

    return _tool_label
