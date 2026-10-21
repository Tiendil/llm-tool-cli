import io
import json
import sys

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.config.tests.fixtures import project_static_settings, runtime_settings
from llm_tool_cli.core.errors import ContextValueNotSet, EnvironmentError
from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.core.settings import StaticConfig, ToolLabel, static_config
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.output import StreamOutputEmitter
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.journal import JournalRecord
from llm_tool_cli.protocol.logic_cells import ContentCell, EnvironmentErrorCell
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.logic_cells.journal import JournalCell
from llm_tool_cli.protocol.logic_cells.warning import WarningCell
from llm_tool_cli.protocol.output_cells import HumanOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell, RenderContext

__all__ = ["isolated_settings", "project_static_settings", "runtime_settings"]
pytestmark = pytest.mark.usefixtures("project_static_settings", "runtime_settings")


class RecordingProcessor:
    def __init__(self, result: Result[None] = Ok(None)) -> None:
        self.records: list[JournalRecord] = []
        self.result = result

    def process(self, record: JournalRecord) -> Result[None]:
        self.records.append(record)
        return self.result


class PositionedOutputCell(OutputCell):
    def render(self, context: RenderContext) -> bytes:
        return f"{context.tool_label} {context.index}/{context.total}: {self.content}\n".encode()


class PositionedLogicCell(LogicCell):
    items: tuple[str, ...]

    def to_journal_record(self) -> JournalRecord:
        return JournalRecord(message="\n".join(self.items))

    def render_human(self) -> list[OutputCell]:
        return [PositionedOutputCell.build_markdown(kind="item", content=text) for text in self.items]

    def render_llm(self) -> list[OutputCell]:
        return []

    def render_automation(self) -> list[OutputCell]:
        return []


class TestStreamOutputEmitter:
    @pytest.mark.parametrize(
        "protocol, actor", [(Protocol.human, "human"), (Protocol.llm, "agent"), (Protocol.automation, "automation")]
    )
    def test_journal__uses_default_factory_and_protocol_actor(self, protocol: Protocol, actor: str) -> None:
        stream = io.StringIO()
        processor = RecordingProcessor()
        emitter = StreamOutputEmitter(stream=stream, journal_processor=processor)
        with runtime_config.scope(RuntimeConfig(protocol=protocol)):
            emitter.journal("starting").unwrap()
        assert len(processor.records) == 1
        assert processor.records[0].message == "starting"
        assert processor.records[0].actor_id == actor
        assert "starting" in stream.getvalue()

    @pytest.mark.parametrize("actor", [None, "worker"])
    def test_journal__custom_factory_receives_explicit_actor_at_each_call(self, actor: str | None) -> None:
        calls: list[tuple[str, str | None]] = []

        def factory(*, message: str, actor_id: str | None) -> JournalCell:
            calls.append((message, actor_id))
            return JournalCell(message=f"{len(calls)}: {message}", actor_id=actor_id)

        processor = RecordingProcessor()
        emitter = StreamOutputEmitter(stream=io.StringIO(), journal_factory=factory, journal_processor=processor)
        emitter.journal("first", actor_id=actor).unwrap()
        emitter.journal("second", actor_id=actor).unwrap()
        assert calls == [("first", actor), ("second", actor)]
        assert [record.message for record in processor.records] == ["1: first", "2: second"]

    def test_emit__direct_cells_do_not_invoke_journal_factory(self) -> None:
        def factory(*, message: str, actor_id: str | None) -> JournalCell:
            raise AssertionError("factory must not run")

        emitter = StreamOutputEmitter(stream=io.StringIO(), journal_factory=factory)
        emitter.emit(
            [EnvironmentErrorCell(error=EnvironmentError(code="failed", message="failure"), is_journal=True)]
        ).unwrap()

    def test_journal__processor_failure_propagates(self) -> None:
        failure = EnvironmentError(code="forward_failed", message="delivery failed")
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream, journal_processor=RecordingProcessor(Err([failure])))
        assert emitter.journal("event").unwrap_err() == [failure]
        assert not stream.getvalue()

    @pytest.mark.parametrize("errors", [[], [EnvironmentError(code="custom_failure", message="unavailable")]])
    def test_emit__processor_failure_disables_forwarding_but_preserves_console_routing(
        self, errors: list[EnvironmentError]
    ) -> None:
        processor = RecordingProcessor(Err(errors))
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream, journal_processor=processor)
        with runtime_config.scope(RuntimeConfig(protocol=Protocol.automation)):
            assert emitter.journal("failed event").unwrap_err() == errors
            emitter.discard()
            emitter.flush()
            assert not stream.getvalue()

            emitter.journal("later event").unwrap()
            emitter.emit(
                [
                    ContentCell(kind="result", media_type="text/plain", content="result"),
                    WarningCell(message="warning", is_journal=True),
                    JournalCell(message="last event"),
                ]
            ).unwrap()
            assert [json.loads(line)["message"] for line in stream.getvalue().splitlines()] == [
                "later event",
                "last event",
            ]
            emitter.flush()

        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert len(records) == 4
        assert records[2]["content"] == "result"
        assert records[3]["message"] == "warning"
        assert [record.message for record in processor.records] == ["failed event"]

    def test_emit__processor_failure_is_local_to_emitter(self) -> None:
        error = EnvironmentError(code="custom_failure", message="unavailable")
        processor = RecordingProcessor(Err([error]))
        first = StreamOutputEmitter(stream=io.StringIO(), journal_processor=processor)
        second = StreamOutputEmitter(stream=io.StringIO(), journal_processor=processor)
        assert first.journal("first").unwrap_err() == [error]
        assert second.journal("second").unwrap_err() == [error]
        assert [record.message for record in processor.records] == ["first", "second"]

    @pytest.mark.parametrize("journal", [False, True])
    def test_render__override_retains_buffering_and_stream_delivery(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str], journal: bool
    ) -> None:
        class CustomOutputEmitter(StreamOutputEmitter):
            def _render(self, cells: list[LogicCell]) -> str:
                return f"Batch of {len(cells)}\n"

        stream = io.StringIO()
        flush = mocker.spy(stream, "flush")
        emitter = CustomOutputEmitter(stream=stream)
        emitter.emit([JournalCell(message="result", is_journal=journal)]).unwrap()
        assert stream.getvalue() == ("Batch of 1\n" if journal else "")
        emitter.flush()
        emitter.flush()
        assert stream.getvalue() == "Batch of 1\n"
        flush.assert_called_once()
        assert not stream.closed
        assert capsys.readouterr() == ("", "")

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_emit__custom_stream_receives_journals_then_results_and_warnings(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str], protocol: Protocol
    ) -> None:
        stream = io.StringIO()
        flush = mocker.spy(stream, "flush")
        processor = RecordingProcessor()
        emitter = StreamOutputEmitter(stream=stream, journal_processor=processor)
        event = JournalCell(message="progress")
        with runtime_config.scope(RuntimeConfig(protocol=protocol)):
            emitter.emit(
                [
                    WarningCell(message="warning"),
                    ContentCell(kind="result", media_type="text/plain", content="completed"),
                    event,
                ]
            ).unwrap()
            assert "progress" in stream.getvalue()
            assert "completed" not in stream.getvalue()
            assert "warning" not in stream.getvalue()
            assert processor.records == [event.to_journal_record()]
            flush.assert_called_once()

            emitter.flush()
            delivered = stream.getvalue()
            assert delivered.index("progress") < delivered.index("completed") < delivered.index("warning")
            assert flush.call_count == 2
            emitter.flush()
            assert stream.getvalue() == delivered
            assert flush.call_count == 2
        assert not stream.closed
        assert capsys.readouterr() == ("", "")

    def test_emit__default_uses_current_stdout_at_delivery(self, mocker: MockerFixture) -> None:
        first = io.StringIO()
        second = io.StringIO()
        mocker.patch.object(sys, "stdout", first)
        emitter = StreamOutputEmitter()
        emitter.emit([ContentCell(kind="result", media_type="text/plain", content="completed")]).unwrap()
        mocker.patch.object(sys, "stdout", second)
        emitter.emit([JournalCell(message="progress")]).unwrap()
        emitter.flush()
        assert not first.getvalue()
        assert second.getvalue().index("progress") < second.getvalue().index("completed")

    @pytest.mark.parametrize("operation", ["write", "flush"])
    def test_flush__stream_failure_propagates_without_retry(self, mocker: MockerFixture, operation: str) -> None:
        stream = io.StringIO()
        failing_operation = mocker.patch.object(stream, operation, side_effect=OSError("delivery failed"))
        emitter = StreamOutputEmitter(stream=stream)
        emitter.emit([ContentCell(kind="result"), WarningCell(message="warning")]).unwrap()
        with pytest.raises(OSError, match="delivery failed"):
            emitter.flush()
        emitter.flush()
        failing_operation.assert_called_once()
        assert not stream.closed

    def test_emit__buffers_results_and_warnings_but_delivers_journals(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        processor = RecordingProcessor()
        emitter = StreamOutputEmitter(journal_processor=processor)
        first = ContentCell(kind="result", media_type="text/plain", content="first")
        event = JournalCell(message="progress")
        last = first.replace(content="last")
        with runtime_config.scope(RuntimeConfig(protocol=Protocol.automation)):
            emitter.emit(
                [WarningCell(message="warning one"), first, event, last, WarningCell(message="warning two")]
            ).unwrap()
            immediate = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
            assert [record["message"] for record in immediate] == ["progress"]
            assert processor.records == [event.to_journal_record()]
            emitter.flush()
            records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
            assert [record["content"] for record in records[:2]] == ["first", "last"]
            assert [record["message"] for record in records[2:]] == ["warning one", "warning two"]
            emitter.flush()
            assert not capsys.readouterr().out
            assert processor.records == [event.to_journal_record()]

    @pytest.mark.parametrize("journal", [False, True])
    @pytest.mark.parametrize("warning", [False, True])
    def test_emit__flags_override_subclass_defaults(
        self, capsys: pytest.CaptureFixture[str], journal: bool, warning: bool
    ) -> None:
        processor = RecordingProcessor()
        emitter = StreamOutputEmitter(journal_processor=processor)
        cell = JournalCell(message="event", is_journal=journal, is_warning=warning)
        emitter.emit([cell]).unwrap()
        assert processor.records == ([cell.to_journal_record()] if journal else [])
        assert bool(capsys.readouterr().out) == (journal and not warning)
        emitter.flush()
        assert bool(capsys.readouterr().out) == (not journal or warning)

    def test_emit__journals_semantic_record_and_preserves_console_projection(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        cell = EnvironmentErrorCell(
            error=EnvironmentError(code="failed", message="failure", ways_to_fix=["Retry."]), is_journal=True
        )
        processor = RecordingProcessor()
        emitter = StreamOutputEmitter(journal_processor=processor)
        emitter.emit([cell]).unwrap()
        assert len(processor.records) == 1
        assert processor.records[0].message == "failure"
        assert processor.records[0].attributes == {"type": "error", "code": "failed"}
        assert "failure\nWay to fix: Retry." in capsys.readouterr().out

    def test_emit__failure_stops_delivery_and_never_replays_processor(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        error = EnvironmentError(code="forward_failed", message="failed")
        processor = RecordingProcessor(Err([error]))
        emitter = StreamOutputEmitter(journal_processor=processor)
        cell = JournalCell(message="failed event", is_warning=True)
        assert emitter.emit([cell, WarningCell(message="unreached")]).unwrap_err() == [error]
        emitter.flush()
        assert not capsys.readouterr().out
        assert processor.records == [cell.to_journal_record()]

    @pytest.mark.parametrize(
        ("items", "expected"),
        [
            ([("café", "second"), (), ("third",)], "  TOOL   0/3: café\n  TOOL   1/3: second\n  TOOL   2/3: third\n"),
            ([("only",)], "  TOOL   0/1: only\n"),
            ([()], ""),
            ([], ""),
        ],
    )
    def test_flush__preserves_projection_order_and_supplies_complete_batch_context(
        self, capsys: pytest.CaptureFixture[str], items: list[tuple[str, ...]], expected: str
    ) -> None:
        emitter = StreamOutputEmitter()
        emitter.emit([PositionedLogicCell(items=values) for values in items]).unwrap()
        with static_config.scope(StaticConfig(tool_label=ToolLabel("  TOOL  "))):
            emitter.flush()
        assert capsys.readouterr() == (expected, "")

    def test_flush__selects_protocol_at_delivery(self, capsys: pytest.CaptureFixture[str]) -> None:
        emitter = StreamOutputEmitter()
        emitter.emit([PositionedLogicCell(items=("hidden",))]).unwrap()
        with runtime_config.scope(RuntimeConfig(protocol=Protocol.llm)):
            emitter.flush()
        assert capsys.readouterr() == ("", "")

    @pytest.mark.parametrize("protocol", [Protocol.human, Protocol.llm])
    @pytest.mark.parametrize("custom_stream", [False, True])
    def test_flush__preserves_unicode_and_protocol_specific_text(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, custom_stream: bool
    ) -> None:
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream if custom_stream else None)
        emitter.emit([ContentCell(kind="message", media_type="text/plain", content="café 日本語")]).unwrap()
        with (
            runtime_config.scope(RuntimeConfig(protocol=protocol)),
            static_config.scope(StaticConfig(tool_label=ToolLabel("  TOOL  "))),
        ):
            emitter.flush()
        captured = capsys.readouterr()
        text = stream.getvalue() if custom_stream else captured.out
        assert (captured.out if custom_stream else stream.getvalue()) == ""
        assert captured.err == ""
        assert "café 日本語" in text
        if protocol == Protocol.human:
            assert text == "café 日本語\n\n"
        else:
            assert text.startswith("--  TOOL  -CELL ")
            assert text.endswith(" END--\n")

    @pytest.mark.parametrize("label", ["FIRST", "SECOND"])
    def test_flush__automation_preserves_cells_and_ignores_label(self, label: str) -> None:
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream)
        cell = ContentCell(kind="message", media_type="text/plain", content="café 日本語", meta={"type": "message"})
        original = cell.model_dump()
        with (
            runtime_config.scope(RuntimeConfig(protocol=Protocol.automation)),
            static_config.scope(StaticConfig(tool_label=ToolLabel(label))),
        ):
            emitter.emit([cell]).unwrap()
            emitter.flush()
            emitter.emit([cell]).unwrap()
            emitter.flush()
        first, second = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert first.pop("id") != second.pop("id")
        assert first == second == {"type": "message", "content": "café 日本語"}
        assert cell.model_dump() == original
        assert stream.getvalue().endswith("\n")

    def test_flush__preserves_error_order_and_guidance(self, capsys: pytest.CaptureFixture[str]) -> None:
        emitter = StreamOutputEmitter()
        emitter.emit(
            [
                EnvironmentErrorCell(error=EnvironmentError(code="first", message="First", ways_to_fix=["Retry."])),
                EnvironmentErrorCell(error=EnvironmentError(code="second", message="Second")),
            ]
        ).unwrap()
        with runtime_config.scope(RuntimeConfig(protocol=Protocol.automation)):
            emitter.flush()
        records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert records[0].pop("id") != records[1].pop("id")
        assert records == [
            {"type": "error", "code": "first", "content": "First\nWay to fix: Retry."},
            {"type": "error", "code": "second", "content": "Second"},
        ]

    def test_flush__missing_initialization_writes_nothing(
        self, isolated_settings: None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        emitter = StreamOutputEmitter()
        emitter.emit([ContentCell(kind="message")]).unwrap()
        with pytest.raises(ContextValueNotSet) as caught:
            emitter.flush()
        assert caught.value.details == {"name": "static_config"}
        assert capsys.readouterr() == ("", "")

    @pytest.mark.parametrize(
        ("last_output", "exception_type"),
        [(ValueError("bad render"), ValueError), (b"\xff", UnicodeDecodeError)],
    )
    def test_flush__render_or_decode_failure_writes_nothing(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
        last_output: bytes | Exception,
        exception_type: type[Exception],
    ) -> None:
        emitter = StreamOutputEmitter()
        emitter.emit([ContentCell(kind="first"), ContentCell(kind="last")]).unwrap()
        mocker.patch.object(HumanOutputCell, "render", side_effect=[b"first", last_output])
        with pytest.raises(exception_type):
            emitter.flush()
        assert not capsys.readouterr().out
        emitter.flush()
        assert not capsys.readouterr().out

    def test_emit__flushes_live_journal_stream(self, mocker: MockerFixture) -> None:
        flush = mocker.spy(sys.stdout, "flush")
        StreamOutputEmitter().emit([JournalCell(message="live")]).unwrap()
        flush.assert_called_once()
