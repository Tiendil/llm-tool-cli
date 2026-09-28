from llm_tool_cli.protocol.cells import Cell
from llm_tool_cli.protocol.formatters.base import Formatter as BaseFormatter


class Formatter(BaseFormatter):
    __slots__ = ("_tool_label",)

    def __init__(self, *, tool_label: str) -> None:
        self._tool_label = tool_label

    def format_cell(self, cell: Cell) -> bytes:  # noqa: CCR001
        id = cell.short_id

        lines = [f"--{self._tool_label}-CELL {id} BEGIN--"]

        lines.append(f"kind={cell.kind}")

        if cell.media_type is not None:
            lines.append(f"media_type={cell.media_type}")

        for meta_key, meta_value in sorted(cell.meta.items()):
            lines.append(f"{meta_key}={meta_value}")

        if cell.content:
            lines.append("")
            lines.append(cell.content.strip())

        lines.append(f"--{self._tool_label}-CELL {id} END--")
        lines.append("")

        return "\n".join(lines).encode()
