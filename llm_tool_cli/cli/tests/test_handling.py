import io
import json
import os
from contextlib import nullcontext
from pathlib import Path

import click
import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.errors import InvalidArguments
from llm_tool_cli.cli.handling import handle_command_errors, report_errors_and_exit
from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.core.errors import EnvironmentError, EnvironmentErrors, InternalError
from llm_tool_cli.core.result import Err, Ok, UnwrapError
from llm_tool_cli.core.settings import initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.output import StreamOutputEmitter, output
from llm_tool_cli.output.errors import JournalCommandFailed
from llm_tool_cli.paths import CacheRootPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells import ContentCell
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.logic_cells.journal import JournalCell
from llm_tool_cli.protocol.logic_cells.warning import WarningCell

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


class TestReportErrorsAndExit:
    @pytest.mark.parametrize("existing_runtime", [False, True])
    @pytest.mark.parametrize("delivery_fails", [False, True])
    def test_reporting_preserves_cache_and_restores_runtime(  # noqa: CCR001 — Runtime and delivery cases.
        self, tmp_path: Path, mocker: MockerFixture, existing_runtime: bool, delivery_fails: bool
    ) -> None:
        initialize(name=ToolName("test"))
        previous = RuntimeConfig(protocol=Protocol.human, cache_dir=CacheRootPath(tmp_path / "cache"))
        observed: list[RuntimeConfig] = []
        stream = io.StringIO()

        class InspectingEmitter(StreamOutputEmitter):
            def _render(self, cells: list[LogicCell]) -> str:
                observed.append(runtime_config.get())
                if delivery_fails:
                    raise OSError("Output unavailable")
                return super()._render(cells)

        for target in (
            "llm_tool_cli.tool_cache.paths.user_cache_path",
            "pathlib.Path.home",
            "pathlib.Path.resolve",
        ):
            mocker.patch(target, side_effect=AssertionError("Diagnostics must not resolve cache paths"))

        scope = runtime_config.scope(previous) if existing_runtime else nullcontext()
        with scope:
            with pytest.raises(OSError if delivery_fails else typer.Exit):
                report_errors_and_exit(
                    [InvalidArguments(reason="Invalid input")],
                    protocol=Protocol.automation,
                    emitter=InspectingEmitter(stream=stream),
                )
            if existing_runtime:
                assert runtime_config.get() == previous
            else:
                assert not runtime_config.is_set()

        expected_cache = previous.cache_dir if existing_runtime else CacheRootPath(Path(os.devnull))
        assert observed == [RuntimeConfig(protocol=Protocol.automation, cache_dir=expected_cache)]
        assert not runtime_config.is_set()
        if delivery_fails:
            assert not stream.getvalue()
        else:
            assert json.loads(stream.getvalue())["reason"] == "Invalid input"

    def test_errors_are_reported_without_journal_processing(self, mocker: MockerFixture) -> None:
        initialize(name=ToolName("test"))
        failures: EnvironmentErrors = [
            InvalidArguments(reason="first\nsecond"),
            EnvironmentError(code="unavailable", message="Service unavailable"),
            JournalCommandFailed(command=["another-tool"], returncode=7, details="failed elsewhere"),
        ]
        original = [error.as_record() for error in failures]
        processor = mocker.Mock()
        processor.process.side_effect = AssertionError("error reporting must not invoke a journal processor")
        factory = mocker.Mock(side_effect=AssertionError("error reporting must not invoke a journal factory"))
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream, journal_processor=processor, journal_factory=factory)
        emitter.emit([ContentCell(kind="success"), WarningCell(message="retained")]).unwrap()
        with pytest.raises(typer.Exit) as caught:
            report_errors_and_exit(failures, protocol=Protocol.automation, emitter=emitter)
        assert caught.value.exit_code == 3
        processor.process.assert_not_called()
        factory.assert_not_called()
        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert [record["code"] for record in records[:3]] == [error.code for error in failures]
        assert records[0]["content"] == "first\nsecond"
        assert records[0]["reason"] == "first\nsecond"
        assert records[3]["message"] == "retained"
        assert len(records) == 4
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
        initialize(name=ToolName("test"))
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

    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("reverse", [False, True])
    def test_ordered_cells_stream_and_highest_exit_code(  # noqa: CCR001
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, reverse: bool
    ) -> None:
        initialize(name=ToolName("test"))
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
            separator = ": " if protocol == Protocol.human else "="
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
        initialize(name=ToolName("test"))

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
        initialize(name=ToolName("test"))
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
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], protocol: Protocol, custom_stream: bool
    ) -> None:
        initialize(name=ToolName("test"))
        stream = io.StringIO()
        emitter = StreamOutputEmitter(stream=stream if custom_stream else None)
        with (
            runtime_config.scope(RuntimeConfig(protocol=protocol, cache_dir=CacheRootPath(tmp_path / "cache"))),
            output.scope(emitter),
        ):
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
