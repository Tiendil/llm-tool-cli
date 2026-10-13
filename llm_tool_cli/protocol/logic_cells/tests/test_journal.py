import json

import pytest

from llm_tool_cli.core.settings import ToolLabel
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells.journal import JournalCell
from llm_tool_cli.protocol.output_cells.base import RenderContext


class TestJournalCell:
    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_render__uses_normalized_multiline_data_and_emits_one_line(self, protocol: Protocol) -> None:
        message = "  first\nsecond\rthird\\n  "
        cell = JournalCell(message=message, actor_id="  actor\nname  ")
        context = RenderContext(index=0, total=1, tool_label=ToolLabel("TEST"))
        rendered = cell.render(protocol)[0].render(context).decode()
        assert cell.message == message.strip()
        assert len(rendered.splitlines()) == 1
        if protocol == Protocol.automation:
            record = json.loads(rendered)
            assert record["message"] == message.strip()
            assert record["actor_id"] == "actor\nname"
            assert "is_journal" not in record
            assert "is_warning" not in record
        else:
            assert r"first\nsecond\rthird\\n" in rendered
            assert r"actor\nname" in rendered

    def test_render__absent_actor_and_empty_message(self) -> None:
        cell = JournalCell(message="")
        context = RenderContext(index=0, total=1, tool_label=ToolLabel("TEST"))
        for protocol in [Protocol.human, Protocol.llm]:
            assert "<->" in cell.render(protocol)[0].render(context).decode()
