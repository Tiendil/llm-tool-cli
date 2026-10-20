import pydantic

from llm_tool_cli.protocol.journal import JournalRecord
from llm_tool_cli.protocol.logic_cells.uniform import UniformCell
from llm_tool_cli.protocol.output_cells import HumanWarningOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell


class WarningCell(UniformCell):
    """A non-fatal diagnostic delivered after ordinary results."""

    is_warning: bool = pydantic.Field(default=True, exclude=True)
    message: str

    def render_human(self) -> list[OutputCell]:
        return [self._render(HumanWarningOutputCell)]

    def to_journal_record(self) -> JournalRecord:
        return JournalRecord(message=self.message, attributes={"type": "warning"})

    def _render(self, cell_type: type[OutputCell]) -> OutputCell:
        return cell_type.build_meta(kind="warning", type="warning", message=self.message)
