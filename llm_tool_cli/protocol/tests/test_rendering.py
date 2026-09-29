import json

import pytest

from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells import ContentCell
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells.base import OutputCell, RenderContext
from llm_tool_cli.protocol.rendering import render_cells


class PositionedOutputCell(OutputCell):
    def render(self, context: RenderContext) -> bytes:
        return f"{context.tool_label} {context.index}/{context.total}: {self.content}\n".encode()


class PositionedLogicCell(LogicCell):
    items: tuple[str, ...]

    def render_human(self) -> list[OutputCell]:
        return [PositionedOutputCell.build_markdown(kind="item", content=text) for text in self.items]

    def render_llm(self) -> list[OutputCell]:
        return []

    def render_automation(self) -> list[OutputCell]:
        return []


class TestRenderCells:
    def test_preserves_sequence_order_and_supplies_context_after_projection(self) -> None:
        cells = (PositionedLogicCell(items=items) for items in [("café", "second"), (), ("third",)])

        rendered = render_cells(cells, protocol=Protocol.human, tool_label="  TOOL  ")

        assert rendered == "  TOOL   0/3: café\n  TOOL   1/3: second\n  TOOL   2/3: third\n".encode()

    def test_single_output_cell_receives_its_own_sequence_context(self) -> None:
        cell = PositionedLogicCell(items=("only",))

        assert render_cells([cell], protocol=Protocol.human, tool_label="TOOL") == b"TOOL 0/1: only\n"

    def test_empty_sequence(self) -> None:
        assert render_cells([], protocol=Protocol.human, tool_label="TOOL") == b""

    def test_empty_projection(self) -> None:
        cell = PositionedLogicCell(items=("only",))

        assert render_cells([cell], protocol=Protocol.llm, tool_label="TOOL") == b""

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_rendering_preserves_logic_cells(self, protocol: Protocol) -> None:
        cell = ContentCell(kind="message", media_type="text/markdown", content="café", meta={"labels": ["one", "two"]})
        original = cell.model_dump()

        render_cells([cell], protocol=protocol, tool_label="TOOL")

        assert cell.model_dump() == original

    @pytest.mark.parametrize("protocol", [Protocol.human, Protocol.llm])
    def test_text_cells_use_context_label_unchanged(self, protocol: Protocol) -> None:
        cell = ContentCell(kind="message")

        output = render_cells([cell], protocol=protocol, tool_label="  LABEL  ")

        assert b"  LABEL  " in output

    def test_automation_ignores_context_label(self) -> None:
        cell = ContentCell(kind="message")

        first = json.loads(render_cells([cell], protocol=Protocol.automation, tool_label="FIRST"))
        second = json.loads(render_cells([cell], protocol=Protocol.automation, tool_label="SECOND"))

        assert first.pop("id") != second.pop("id")
        assert first == second == {"content": None}
