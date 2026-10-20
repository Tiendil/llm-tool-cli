import pytest

from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells.warning import WarningCell
from llm_tool_cli.protocol.output_cells import AutomationOutputCell, HumanWarningOutputCell, LLMOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell


class TestWarningCell:
    def test_to_journal_record__retains_warning_message(self) -> None:
        cell = WarningCell(message="first\nsecond", is_journal=True)
        record = cell.to_journal_record()
        assert record.message == "first\nsecond"
        assert record.attributes == {"type": "warning"}

    @pytest.mark.parametrize(
        ("protocol", "output_type"),
        [
            (Protocol.human, HumanWarningOutputCell),
            (Protocol.llm, LLMOutputCell),
            (Protocol.automation, AutomationOutputCell),
        ],
    )
    def test_render__preserves_warning_payload_without_delivery_flags(
        self, protocol: Protocol, output_type: type[OutputCell]
    ) -> None:
        cell = WarningCell(message="first\nsecond", is_warning=False)
        rendered = cell.render(protocol)
        assert len(rendered) == 1
        assert isinstance(rendered[0], output_type)
        assert rendered[0].kind == "warning"
        assert rendered[0].content is None
        assert rendered[0].meta == {"type": "warning", "message": "first\nsecond"}
        assert "is_warning" not in cell.model_dump()
