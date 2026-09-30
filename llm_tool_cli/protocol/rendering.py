from collections.abc import Iterable

from llm_tool_cli.core.settings import get_tool_label
from llm_tool_cli.protocol.entities import Protocol
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells.base import RenderContext
from llm_tool_cli.protocol.streams import write_output


def render_cells(cells: Iterable[LogicCell], *, protocol: Protocol) -> bytes:
    tool_label = get_tool_label()
    sequence = [output for cell in cells for output in cell.render(protocol)]
    return b"".join(
        cell.render(RenderContext(index=index, total=len(sequence), tool_label=tool_label))
        for index, cell in enumerate(sequence)
    )


def write_cells(cells: Iterable[LogicCell], *, protocol: Protocol, stderr: bool = False) -> None:
    write_output(render_cells(cells, protocol=protocol).decode("utf-8"), error=stderr)
