from pathlib import Path

import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.context import CommandContext, global_options
from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol

__all__ = ["isolated_settings"]


@pytest.fixture
def app() -> typer.Typer:
    application = create_app(help="Inspect test resources.")

    @application.command(help="Show a test resource.")
    def show() -> None:
        raise AssertionError("Help and completion must not execute the command.")

    return application


class TestCreateApp:
    @pytest.mark.parametrize("option", ["-p", "--protocol"])
    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_nested_commands_and_repeated_invocations(self, option: str, protocol: Protocol) -> None:
        application = create_app(help="Inspect nested resources.")
        group = typer.Typer()
        application.add_typer(group, name="nested")
        received: list[GlobalOptions] = []

        @group.command()
        def show(context: typer.Context) -> None:
            received.append(global_options.get())
            assert context.obj == {"other": "state"}
            assert context.find_root().meta == {}

        runner = CliRunner()
        explicit = runner.invoke(
            application,
            [option, protocol.value, "--config", "~/custom.toml", "nested", "show"],
            obj={"other": "state"},
        )
        assert not global_options.is_set()
        unspecified = runner.invoke(application, ["nested", "show"], obj={"other": "state"})
        assert not global_options.is_set()

        assert explicit.exit_code == unspecified.exit_code == 0
        assert explicit.stdout == explicit.stderr == unspecified.stdout == unspecified.stderr == ""
        assert received == [
            GlobalOptions(protocol=protocol, config_path=ProjectConfigPath(Path("~/custom.toml"))),
            GlobalOptions(),
        ]

    @pytest.mark.parametrize(
        ("failure", "exit_code"),
        [(None, 0), (typer.Exit(7), 7), (RuntimeError("command failed"), 1)],
    )
    def test_restores_outer_options_after_command(self, failure: Exception | None, exit_code: int) -> None:
        application = create_app(help="Inspect scoped options.")
        received: list[GlobalOptions] = []

        @application.command()
        def show(context: typer.Context) -> None:
            command = CommandContext(context)
            received.append(command.global_options)
            assert command.protocol == Protocol.human
            if failure is not None:
                raise failure

        outer = GlobalOptions(protocol=Protocol.automation, config_path=ProjectConfigPath(Path("outer.toml")))
        with global_options.scope(outer):
            result = CliRunner().invoke(application, ["show"])

            assert result.exit_code == exit_code
            assert received == [GlobalOptions()]
            assert global_options.get() == outer

        assert not global_options.is_set()
        if failure is not None and not isinstance(failure, typer.Exit):
            assert isinstance(result.exception, type(failure))
            assert result.exception.args == failure.args

    def test_subcommand_parse_error_clears_options(self, app: typer.Typer) -> None:
        result = CliRunner().invoke(app, ["-p", "automation", "show", "--unknown"])

        assert result.exit_code == 2
        assert "No such option" in result.stderr
        assert not global_options.is_set()

    def test_invalid_protocol_stops_execution(self, app: typer.Typer, isolated_settings: None) -> None:
        initialize(label=ToolLabel("TEST"))

        result = CliRunner().invoke(app, ["--protocol", "invalid", "show"])

        assert result.exit_code == 1
        assert not result.stdout
        assert result.stderr.startswith("--TEST-CELL ")
        assert result.stderr.count(" BEGIN--\n") == 1
        assert "code=invalid_arguments\n" in result.stderr

    @pytest.mark.parametrize("option", ["-p", "--protocol", "--config"])
    def test_missing_option_value(self, app: typer.Typer, option: str) -> None:
        result = CliRunner().invoke(app, [option])

        assert result.exit_code == 2
        assert not result.stdout
        assert "requires an argument" in result.stderr

    @pytest.mark.parametrize("option", ["-h", "--help"])
    @pytest.mark.parametrize("command", [[], ["show"]])
    def test_help_aliases(self, app: typer.Typer, option: str, command: list[str]) -> None:
        result = CliRunner().invoke(app, [*command, option])

        assert result.exit_code == 0
        assert not result.stderr
        assert not global_options.is_set()
        assert ("Show a test resource." if command else "Inspect test resources.") in result.stdout
        assert "--help" in result.stdout
        assert "-h" in result.stdout
        if not command:
            assert "--protocol" in result.stdout
            assert "-p" in result.stdout
            assert "--config" in result.stdout
            assert "--show-completion" in result.stdout
            assert "--install-completion" in result.stdout

    def test_show_completion_does_not_install(self, app: typer.Typer, mocker: MockerFixture) -> None:
        mocker.patch("typer.completion._get_shell_name", return_value="bash")
        install = mocker.patch("typer.completion.install")

        result = CliRunner().invoke(app, ["--show-completion"], prog_name="sample")

        assert result.exit_code == 0
        assert not result.stderr
        assert "_SAMPLE_COMPLETE" in result.stdout
        assert "complete" in result.stdout
        install.assert_not_called()

    def test_install_completion_is_explicit(self, app: typer.Typer, mocker: MockerFixture) -> None:
        install = mocker.patch("typer.completion.install", return_value=("bash", "/test/completion.sh"))

        assert CliRunner().invoke(app, ["--help"]).exit_code == 0
        install.assert_not_called()

        result = CliRunner().invoke(app, ["--install-completion"])

        assert result.exit_code == 0
        assert not result.stderr
        install.assert_called_once_with()

    def test_applications_have_independent_commands(self, app: typer.Typer) -> None:
        other = create_app(help="Other resources.")

        result = CliRunner().invoke(other, ["show"])

        assert result.exit_code == 2
        assert "No such command" in result.stderr
