import io
import json

import click
import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.errors import InvalidArguments
from llm_tool_cli.cli.handling import handle_command_errors, report_errors_and_exit
from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core.errors import EnvironmentError, EnvironmentErrors, InternalError
from llm_tool_cli.core.result import Err, Ok, UnwrapError
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.output import StreamOutputEmitter, output
from llm_tool_cli.output.errors import JournalCommandFailed
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.journal import JournalRecord
from llm_tool_cli.protocol.logic_cells import ContentCell
from llm_tool_cli.protocol.logic_cells.journal import JournalCell
from llm_tool_cli.protocol.logic_cells.warning import WarningCell

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


class TestReportErrorsAndExit:
    @pytest.mark.parametrize(
        "delivery_failure",
        [
            JournalCommandFailed(command=["journal-tool"], returncode=7, details="failed"),
            EnvironmentError(code="custom_failure", message="unavailable"),
        ],
    )
    @pytest.mark.parametrize("fail_at", [0, 1, 2])
    def test_journal_failure_preserves_all_errors_and_warnings_without_retry(
        self, mocker: MockerFixture, fail_at: int, delivery_failure: EnvironmentError
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        failures: EnvironmentErrors = [
            InvalidArguments(reason="first"),
            InvalidArguments(reason="second"),
            InvalidArguments(reason="third"),
        ]
        original = [error.as_record() for error in failures]
        processor = mocker.Mock()
        processor.process.side_effect = [*[Ok(None) for _ in range(fail_at)], Err([delivery_failure])]

        def factory(*, message: str, actor_id: str | None) -> JournalCell:
            raise AssertionError("terminal errors must not invoke a tool factory")

        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream, journal_processor=processor, journal_factory=factory)
        emitter.emit([ContentCell(kind="success"), WarningCell(message="retained")]).unwrap()
        with pytest.raises(typer.Exit) as caught:
            report_errors_and_exit(failures, protocol=Protocol.automation, emitter=emitter)
        assert caught.value.exit_code == 3
        assert processor.process.call_count == fail_at + 1
        assert [call.args[0].message for call in processor.process.call_args_list] == ["first", "second", "third"][
            : fail_at + 1
        ]
        assert all(isinstance(call.args[0], JournalRecord) for call in processor.process.call_args_list)
        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert [record["content"] for record in records[:3]] == ["first", "second", "third"]
        assert records[3]["code"] == delivery_failure.code
        assert records[4]["message"] == "retained"
        assert len(records) == 5
        assert [error.as_record() for error in failures] == original

    @pytest.mark.parametrize("reverse", [False, True])
    @pytest.mark.parametrize(
        "delivery_failure",
        [
            JournalCommandFailed(command=["tool"], returncode=None, details="unavailable"),
            EnvironmentError(code="custom_failure", message="unavailable"),
        ],
    )
    def test_failed_emitter_is_not_retried_when_reporting_mixed_errors(
        self, mocker: MockerFixture, reverse: bool, delivery_failure: EnvironmentError
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        processor = mocker.Mock()
        processor.process.return_value = Err([delivery_failure])
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream, journal_processor=processor)
        failed = emitter.emit([JournalCell(message="failed event")])
        errors: EnvironmentErrors = [InvalidArguments(reason="original"), *failed.unwrap_err()]
        if reverse:
            errors.reverse()
        with pytest.raises(typer.Exit):
            report_errors_and_exit(errors, protocol=Protocol.automation, emitter=emitter)
        assert [json.loads(line)["code"] for line in stream.getvalue().splitlines()] == [
            error.code for error in errors
        ]
        processor.process.assert_called_once()

    def test_error_type_does_not_disable_a_healthy_processor(self, mocker: MockerFixture) -> None:
        initialize(label=ToolLabel("TEST"))
        processor = mocker.Mock()
        processor.process.return_value = Ok(None)
        stream = io.StringIO()
        error = JournalCommandFailed(command=["another-tool"], returncode=7, details="failed elsewhere")
        with pytest.raises(typer.Exit):
            report_errors_and_exit(
                [error],
                protocol=Protocol.automation,
                emitter=StreamOutputEmitter(stream=stream, journal_processor=processor),
            )
        processor.process.assert_called_once()
        assert processor.process.call_args.args[0].attributes["code"] == error.code
        assert json.loads(stream.getvalue())["code"] == error.code

    def test_successful_journaling_preserves_error_details_and_emits_one_diagnostic(
        self, mocker: MockerFixture
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        processor = mocker.Mock()
        processor.process.return_value = Ok(None)
        stream = io.StringIO()
        error = InvalidArguments(reason="first\nsecond")
        with pytest.raises(typer.Exit):
            report_errors_and_exit(
                [error],
                protocol=Protocol.automation,
                emitter=StreamOutputEmitter(stream=stream, journal_processor=processor),
            )
        processor.process.assert_called_once()
        record = processor.process.call_args.args[0]
        assert record.message == "first\nsecond"
        assert record.attributes == {"type": "error", "code": "invalid_arguments", "reason": "first\nsecond"}
        assert record.actor_id is None
        assert len(stream.getvalue().splitlines()) == 1
        assert json.loads(stream.getvalue())["content"] == "first\nsecond"

    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("reverse", [False, True])
    def test_ordered_cells_stream_and_highest_exit_code(  # noqa: CCR001
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, reverse: bool
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        errors: EnvironmentErrors = [
            InvalidArguments(reason="Invalid café 日本語"),
            EnvironmentError(code="unavailable", message="Service unavailable"),
        ]
        if reverse:
            errors.reverse()
        original = [error.as_record() for error in errors]

        with pytest.raises(typer.Exit) as caught:
            report_errors_and_exit(errors, protocol=protocol)

        assert caught.value.exit_code == 3
        assert [error.as_record() for error in errors] == original
        captured = capsys.readouterr()
        if protocol == Protocol.automation:
            assert not captured.err
            records = [json.loads(line) for line in captured.out.splitlines()]
            for record in records:
                assert record.pop("id")
            expected = [{**record, "content": record["message"]} for record in original]
            for record in expected:
                del record["message"]
            assert records == expected
        else:
            assert not captured.err
            separator = " = " if protocol == Protocol.human else "="
            codes = [f"code{separator}{error.code}\n" for error in errors]
            assert all(code in captured.out for code in codes)
            positions = [captured.out.index(code) for code in codes]
            assert positions == sorted(positions)
            assert "café 日本語" in captured.out
            assert "cli_exit_code" not in captured.out

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_empty_errors_exit_successfully_without_output(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol
    ) -> None:
        initialize(label=ToolLabel("TEST"))

        with pytest.raises(typer.Exit) as caught:
            report_errors_and_exit([], protocol=protocol)

        assert caught.value.exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""


class TestHandleCommandErrors:
    def test_success_continues_without_output_or_exit(self, capsys: pytest.CaptureFixture[str]) -> None:
        with handle_command_errors(protocol=Protocol.llm):
            value = Ok("completed").unwrap()

        assert value == "completed"
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_failed_command_stops_and_reports_errors(self, protocol: Protocol) -> None:
        initialize(label=ToolLabel("TEST"))
        app = typer.Typer()

        @app.command()
        def fail() -> None:
            with handle_command_errors(protocol=protocol):
                Err([InvalidArguments(reason="invalid argument")]).unwrap()
                typer.echo("unreachable")
            typer.echo("also unreachable")

        result = CliRunner().invoke(app, [])

        assert result.exit_code == 1
        assert "unreachable" not in result.output
        if protocol == Protocol.automation:
            assert not result.stderr
            assert json.loads(result.stdout)["code"] == "invalid_arguments"
        else:
            assert not result.stderr
            assert "invalid_arguments" in result.stdout

    @pytest.mark.parametrize(
        "failure",
        [RuntimeError("bug"), InternalError("broken state"), typer.Exit(7), click.UsageError("bad usage")],
    )
    def test_unrelated_exceptions_propagate_without_output(
        self, capsys: pytest.CaptureFixture[str], failure: Exception
    ) -> None:
        with pytest.raises(type(failure)) as caught:
            with handle_command_errors(protocol=Protocol.llm):
                raise failure

        assert caught.value == failure
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""

    @pytest.mark.parametrize("payload", [None, "invalid", [InvalidArguments(reason="invalid"), "malformed"]])
    def test_malformed_unwrap_error_propagates_without_partial_output(
        self, capsys: pytest.CaptureFixture[str], payload: object
    ) -> None:
        failure = UnwrapError(error=[])
        failure.details["error"] = payload

        with pytest.raises(UnwrapError) as caught:
            with handle_command_errors(protocol=Protocol.llm):
                raise failure

        assert caught.value == failure
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""

    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("custom_stream", [False, True])
    def test_discard__failure_outputs_error_then_warnings_without_results(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, custom_stream: bool
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream if custom_stream else None)
        with runtime_config.scope(RuntimeConfig(protocol=protocol)), output.scope(emitter):
            with pytest.raises(typer.Exit) as caught:
                with handle_command_errors(protocol=protocol):
                    emitter.emit([ContentCell(kind="success"), WarningCell(message="keep warning")]).unwrap()
                    Err([EnvironmentError(code="failed", message="command failed")]).unwrap()
        assert caught.value.exit_code == 3
        captured = capsys.readouterr()
        delivered = stream.getvalue() if custom_stream else captured.out
        assert not (captured.out if custom_stream else stream.getvalue())
        assert not captured.err
        assert "success" not in delivered
        assert delivered.index("command failed") < delivered.index("keep warning")
        assert not stream.closed
        if protocol == Protocol.automation:
            assert [json.loads(line)["type"] for line in delivered.splitlines()] == ["error", "warning"]

    def test_discard__unexpected_failure_does_not_flush_results(self, capsys: pytest.CaptureFixture[str]) -> None:
        emitter = StreamOutputEmitter()
        with output.scope(emitter), pytest.raises(RuntimeError, match="defect"):
            with handle_command_errors(protocol=Protocol.human):
                emitter.emit([ContentCell(kind="success")]).unwrap()
                raise RuntimeError("defect")
        emitter.flush()
        assert not capsys.readouterr().out
