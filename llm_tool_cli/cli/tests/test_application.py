import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.application import create_app


@pytest.fixture
def app() -> typer.Typer:
    application = create_app(help="Inspect test resources.")

    @application.callback()
    def root() -> None:
        pass

    @application.command(help="Show a test resource.")
    def show() -> None:
        raise AssertionError("Help and completion must not execute the command.")

    return application


class TestCreateApp:
    @pytest.mark.parametrize("option", ["-h", "--help"])
    @pytest.mark.parametrize("command", [[], ["show"]])
    def test_help_aliases(self, app: typer.Typer, option: str, command: list[str]) -> None:
        result = CliRunner().invoke(app, [*command, option])

        assert result.exit_code == 0
        assert not result.stderr
        assert ("Show a test resource." if command else "Inspect test resources.") in result.stdout
        assert "--help" in result.stdout
        assert "-h" in result.stdout
        if not command:
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

        @other.callback()
        def root() -> None:
            pass

        result = CliRunner().invoke(other, ["show"])

        assert result.exit_code == 2
        assert "No such command" in result.stderr
