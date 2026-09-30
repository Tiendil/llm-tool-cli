import io
import json
import sys

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.core.errors import ToolLabelNotInitialized
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells import ContentCell
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells.base import OutputCell, RenderContext
from llm_tool_cli.protocol.rendering import render_cells, write_cells

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


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
        initialize(tool_label=ToolLabel("  TOOL  "))
        cells = (PositionedLogicCell(items=items) for items in [("café", "second"), (), ("third",)])

        rendered = render_cells(cells, protocol=Protocol.human)

        assert rendered == "  TOOL   0/3: café\n  TOOL   1/3: second\n  TOOL   2/3: third\n".encode()

    def test_single_output_cell_receives_its_own_sequence_context(self) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        cell = PositionedLogicCell(items=("only",))

        assert render_cells([cell], protocol=Protocol.human) == b"TOOL 0/1: only\n"

    def test_empty_sequence(self) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        assert render_cells([], protocol=Protocol.human) == b""

    def test_empty_projection(self) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        cell = PositionedLogicCell(items=("only",))

        assert render_cells([cell], protocol=Protocol.llm) == b""

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_rendering_preserves_logic_cells(self, protocol: Protocol) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        cell = ContentCell(kind="message", media_type="text/markdown", content="café", meta={"labels": ["one", "two"]})
        original = cell.model_dump()

        render_cells([cell], protocol=protocol)

        assert cell.model_dump() == original

    @pytest.mark.parametrize("protocol", [Protocol.human, Protocol.llm])
    def test_text_cells_use_context_label_unchanged(self, protocol: Protocol) -> None:
        initialize(tool_label=ToolLabel("  LABEL  "))
        cell = ContentCell(kind="message")

        output = render_cells([cell], protocol=protocol)

        assert b"  LABEL  " in output

    @pytest.mark.parametrize("label", ["FIRST", "SECOND"])
    def test_automation_ignores_context_label(self, label: str) -> None:
        initialize(tool_label=ToolLabel(label))
        cell = ContentCell(kind="message")

        first = json.loads(render_cells([cell], protocol=Protocol.automation))
        second = json.loads(render_cells([cell], protocol=Protocol.automation))

        assert first.pop("id") != second.pop("id")
        assert first == second == {"content": None}

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_requires_initialization(self, protocol: Protocol) -> None:
        with pytest.raises(ToolLabelNotInitialized):
            render_cells([ContentCell(kind="message")], protocol=protocol)


class TestWriteCells:
    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("stderr", [False, True])
    def test_unicode_and_stream_selection(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, stderr: bool
    ) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        cell = ContentCell(kind="message", media_type="text/markdown", content="café 日本語", meta={"type": "message"})

        write_cells([cell], protocol=protocol, stderr=stderr)

        captured = capsys.readouterr()
        output = captured.err if stderr else captured.out
        assert (captured.out if stderr else captured.err) == ""
        if protocol == Protocol.automation:
            records = [json.loads(line) for line in output.splitlines()]
            assert len(records) == 1
            assert records[0].pop("id")
            assert records == [{"content": "café 日本語", "type": "message"}]
            assert output.endswith("\n")
        else:
            assert "café 日本語" in output
            if protocol == Protocol.human:
                assert output.startswith("----- TOOL CELL ")
                assert output.endswith("\n\n")
            else:
                assert output.startswith("--TOOL-CELL ")
                assert output.endswith(" END--\n")

    def test_generator_batch_uses_stdout_by_default(self, capsys: pytest.CaptureFixture[str]) -> None:
        initialize(tool_label=ToolLabel("  TOOL  "))
        cells = (PositionedLogicCell(items=items) for items in [("café", "second"), (), ("third",)])

        write_cells(cells, protocol=Protocol.human)

        captured = capsys.readouterr()
        assert captured.out == "  TOOL   0/3: café\n  TOOL   1/3: second\n  TOOL   2/3: third\n"
        assert captured.err == ""

    @pytest.mark.parametrize("cells", [[], [PositionedLogicCell(items=())]])
    def test_empty_output(self, capsys: pytest.CaptureFixture[str], cells: list[LogicCell]) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        write_cells(cells, protocol=Protocol.human)

        captured = capsys.readouterr()
        assert captured.out == captured.err == ""

    @pytest.mark.parametrize(
        ("last_output", "exception_type"),
        [(RuntimeError("render failed"), RuntimeError), (b"\xff", UnicodeDecodeError)],
    )
    def test_render_or_decode_failure_writes_nothing(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
        last_output: bytes | Exception,
        exception_type: type[Exception],
    ) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        mocker.patch.object(PositionedOutputCell, "render", side_effect=[b"first\n", last_output])
        cell = PositionedLogicCell(items=("first", "second"))

        with pytest.raises(exception_type):
            write_cells([cell], protocol=Protocol.human)

        captured = capsys.readouterr()
        assert captured.out == captured.err == ""

    def test_stream_failure_propagates(self, mocker: MockerFixture) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        stream = io.StringIO()
        mocker.patch.object(stream, "write", side_effect=OSError("write failed"))
        mocker.patch.object(sys, "stdout", stream)

        with pytest.raises(OSError, match="write failed"):
            write_cells([ContentCell(kind="message")], protocol=Protocol.human)

    def test_missing_initialization_writes_nothing(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(ToolLabelNotInitialized):
            write_cells([ContentCell(kind="message")], protocol=Protocol.llm, stderr=True)

        captured = capsys.readouterr()
        assert captured.out == captured.err == ""
