import pytest

from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells.warning import WarningCell


class TestWarningCell:
    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_render__preserves_warning_payload_without_delivery_flags(self, protocol: Protocol) -> None:
        cell = WarningCell(message="first\nsecond", is_warning=False)
        rendered = cell.render(protocol)
        assert len(rendered) == 1
        assert rendered[0].kind == "warning"
        assert rendered[0].content is None
        assert rendered[0].meta == {"type": "warning", "message": "first\nsecond"}
        assert "is_warning" not in cell.model_dump()
