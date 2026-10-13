import datetime

import pydantic

from llm_tool_cli.protocol.journal import JournalRecord
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells.base import OutputCell, to_meta_value
from llm_tool_cli.protocol.output_cells.journal import JournalAutomationOutputCell, JournalTextOutputCell


class JournalCell(LogicCell):
    """A journal event with compact text and structured automation projections."""

    is_journal: bool = pydantic.Field(default=True, exclude=True)
    timestamp: datetime.datetime = pydantic.Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    actor_id: str | None = None
    message: str

    def to_journal_record(self) -> JournalRecord:
        return JournalRecord(
            message=self.message,
            timestamp=self.timestamp,
            actor_id=self.actor_id,
            attributes=self.model_dump(mode="json", exclude={"message", "timestamp", "actor_id"}),
        )

    def human_line(self) -> str:
        return f"{self.timestamp.time().isoformat('seconds')} <{self.actor_id or '-'}> {self.message}"

    def llm_line(self) -> str:
        return f"{self.timestamp.isoformat()} <{self.actor_id or '-'}> {self.message}"

    def render_human(self) -> list[OutputCell]:
        return [JournalTextOutputCell.build(kind="journal", media_type="text/plain", content=self.human_line())]

    def render_llm(self) -> list[OutputCell]:
        return [JournalTextOutputCell.build(kind="journal", media_type="text/plain", content=self.llm_line())]

    def render_automation(self) -> list[OutputCell]:
        return [
            JournalAutomationOutputCell.build_meta(
                kind="journal", **{key: to_meta_value(value) for key, value in self.model_dump(mode="json").items()}
            )
        ]
