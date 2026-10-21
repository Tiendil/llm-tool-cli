import pytest

from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.errors import JournalConversionUnsupported
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells import AutomationOutputCell, HumanOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell


class ExampleLogicCell(LogicCell):
    items: tuple[str, ...]

    def render_human(self) -> list[OutputCell]:
        return [HumanOutputCell.build_markdown(kind="item", content=item) for item in self.items]

    def render_llm(self) -> list[OutputCell]:
        return []

    def render_automation(self) -> list[OutputCell]:
        return [AutomationOutputCell.build_meta(kind="items", items=list(self.items))]


class TestLogicCell:
    def test_to_journal_record__unsupported_conversion_is_explicit(self) -> None:
        cell = ExampleLogicCell(items=("first", "second"))

        with pytest.raises(JournalConversionUnsupported) as caught:
            cell.to_journal_record()

        assert caught.value.details == {"cell_type": "ExampleLogicCell"}

    @pytest.mark.parametrize(
        ("protocol", "expected"),
        (
            (Protocol.human, [("item", "first"), ("item", "second")]),
            (Protocol.llm, []),
            (Protocol.automation, [("items", None)]),
        ),
    )
    def test_render__dispatches_to_protocol_projection(
        self, protocol: Protocol, expected: list[tuple[str, str | None]]
    ) -> None:
        cell = ExampleLogicCell(items=("first", "second"))

        result = cell.render(protocol)

        assert [(output.kind, output.content) for output in result] == expected
