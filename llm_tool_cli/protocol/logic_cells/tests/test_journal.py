import json

import pytest

from llm_tool_cli.core.settings import ToolLabel
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells.journal import JournalCell
from llm_tool_cli.protocol.output_cells.base import RenderContext


class TestJournalCell:
    def test_to_journal_record__preserves_timestamp_and_subclass_fields(self) -> None:
        class EventCell(JournalCell):
            task_id: str | None = None

        cell = EventCell(message="event", actor_id="actor", task_id="T-1", is_warning=True)
        original = cell.model_dump()
        record = cell.to_journal_record()
        assert record.timestamp == cell.timestamp
        assert record.message == cell.message
        assert record.actor_id == "actor"
        assert record.attributes == {"task_id": "T-1"}
        assert cell.model_dump() == original

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
