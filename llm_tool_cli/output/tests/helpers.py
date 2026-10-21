from llm_tool_cli.core.result import Ok, Result
from llm_tool_cli.output import JournalCellFactory, StreamOutputEmitter, output
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.logic_cells.journal import JournalCell
from llm_tool_cli.protocol.logic_cells.warning import WarningCell


class CollectingEmitter(StreamOutputEmitter):
    """Capture submitted logical cells without rendering or external side effects."""

    def __init__(self, *, journal_factory: JournalCellFactory = JournalCell) -> None:
        super().__init__(journal_factory=journal_factory)
        self.cells: list[LogicCell] = []

    def emit(self, cells: list[LogicCell]) -> Result[None]:
        self.cells.extend(cells)
        return Ok(None)

    def flush(self) -> None:
        pass

    def discard(self) -> None:
        self.cells = [cell for cell in self.cells if cell.is_warning]


def warning_messages() -> list[str]:
    emitter = output.get()
    assert isinstance(emitter, CollectingEmitter)
    return [cell.message for cell in emitter.cells if isinstance(cell, WarningCell)]
