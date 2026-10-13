import sys
from types import EllipsisType
from typing import Protocol, TextIO

from llm_tool_cli.config.runtime import runtime_config
from llm_tool_cli.core import settings
from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.core.result import Ok, Result, unwrap_to_error
from llm_tool_cli.output.journal import JournalProcessor, NoopJournalProcessor
from llm_tool_cli.protocol import Protocol as OutputProtocol
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.logic_cells.journal import JournalCell
from llm_tool_cli.protocol.output_cells.base import RenderContext


class JournalCellFactory(Protocol):
    __slots__ = ()

    def __call__(self, *, message: str, actor_id: str | None) -> JournalCell: ...  # noqa: E704


class OutputEmitter(Protocol):
    __slots__ = ()

    def emit(self, cells: list[LogicCell]) -> Result[None]: ...  # noqa: E704

    def journal(self, message: str, *, actor_id: str | None | EllipsisType = ...) -> Result[None]: ...  # noqa: E704

    def flush(self) -> None: ...  # noqa: E704

    def discard(self) -> None:
        """Discard pending ordinary results, retaining warnings for failure reporting."""
        ...


output = ContextValue[OutputEmitter]("output")


class StreamOutputEmitter:
    """Deliver journals now, then buffered results and warnings at finalization."""

    __slots__ = ("_cells", "_warnings", "_stream", "_journal_failed", "journal_processor", "journal_factory")

    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        journal_processor: JournalProcessor | None = None,
        journal_factory: JournalCellFactory = JournalCell,
    ) -> None:
        self._stream = stream
        self.journal_processor = journal_processor if journal_processor is not None else NoopJournalProcessor()
        self.journal_factory = journal_factory
        # A processor failure disables forwarding for this emitter's lifetime.
        self._journal_failed = False
        self._cells: list[LogicCell] = []
        self._warnings: list[LogicCell] = []

    def journal(self, message: str, *, actor_id: str | None | EllipsisType = ...) -> Result[None]:
        if actor_id is ...:
            protocol = runtime_config.get().protocol
            actor_id = "agent" if protocol == OutputProtocol.llm else protocol.value
        return self.emit([self.journal_factory(message=message, actor_id=actor_id)])

    @unwrap_to_error
    def emit(self, cells: list[LogicCell]) -> Result[None]:  # noqa: CCR001
        for cell in cells:
            if cell.is_journal and not self._journal_failed:
                processed = self.journal_processor.process(cell.to_journal_record())
                if processed.is_err():
                    self._journal_failed = True
                    return processed
            if cell.is_warning:
                self._warnings.append(cell)
            elif cell.is_journal:
                self._write([cell])
            else:
                self._cells.append(cell)
        return Ok(None)

    def flush(self) -> None:
        cells = [*self._cells, *self._warnings]
        self._cells.clear()
        self._warnings.clear()
        self._write(cells)

    def discard(self) -> None:
        self._cells.clear()

    def _write(self, cells: list[LogicCell]) -> None:
        if not cells:
            return
        # Render the complete batch before writing so rendering failures cannot
        # expose partial output. A failed stream write is not retried.
        text = self._render(cells)
        stream = self._stream if self._stream is not None else sys.stdout
        stream.write(text)
        stream.flush()

    def _render(self, cells: list[LogicCell]) -> str:
        """Prepare complete batch text; subclasses may override without handling streams."""
        protocol = runtime_config.get().protocol
        tool_label = settings.static_config.get().tool_label
        sequence = [output_cell for cell in cells for output_cell in cell.render(protocol)]
        return b"".join(
            cell.render(RenderContext(index=index, total=len(sequence), tool_label=tool_label))
            for index, cell in enumerate(sequence)
        ).decode("utf-8")
