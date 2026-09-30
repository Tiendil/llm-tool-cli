import json

import click
import pytest
import typer
from typer.testing import CliRunner

from llm_tool_cli.cli.errors import InvalidArguments
from llm_tool_cli.cli.handling import handle_command_errors, report_errors_and_exit
from llm_tool_cli.core.errors import EnvironmentError, EnvironmentErrors, InternalError
from llm_tool_cli.core.result import Err, Ok, UnwrapError
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.protocol import Protocol

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


class TestReportErrorsAndExit:
    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("reverse", [False, True])
    def test_ordered_cells_stream_and_highest_exit_code(  # noqa: CCR001
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, reverse: bool
    ) -> None:
        initialize(tool_label=ToolLabel("TEST"))
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
            assert not captured.out
            separator = " = " if protocol == Protocol.human else "="
            codes = [f"code{separator}{error.code}\n" for error in errors]
            assert all(code in captured.err for code in codes)
            positions = [captured.err.index(code) for code in codes]
            assert positions == sorted(positions)
            assert "café 日本語" in captured.err
            assert "cli_exit_code" not in captured.err

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_empty_errors_exit_successfully_without_output(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol
    ) -> None:
        initialize(tool_label=ToolLabel("TEST"))

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
        initialize(tool_label=ToolLabel("TEST"))
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
            assert not result.stdout
            assert "invalid_arguments" in result.stderr

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
