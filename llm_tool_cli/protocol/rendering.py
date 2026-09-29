from collections.abc import Iterable

from llm_tool_cli.protocol.entities import Protocol
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells.base import RenderContext


def render_cells(cells: Iterable[LogicCell], *, protocol: Protocol, tool_label: str) -> bytes:
    sequence = [output for cell in cells for output in cell.render(protocol)]
    return b"".join(
        cell.render(RenderContext(index=index, total=len(sequence), tool_label=tool_label))
        for index, cell in enumerate(sequence)
    )
