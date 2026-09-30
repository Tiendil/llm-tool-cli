from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from llm_tool_cli.cli.options import ConfigOption, ProtocolOption
from llm_tool_cli.core import settings
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol

__all__ = ["isolated_settings"]


@pytest.fixture
def protocol_app(isolated_settings: None) -> typer.Typer:
    settings.initialize(tool_label=settings.ToolLabel("TEST"))
    app = typer.Typer()

    @app.callback()
    def initialize(protocol: ProtocolOption = None) -> None:
        typer.echo("unspecified" if protocol is None else protocol.value)

    @app.command()
    def show() -> None:
        pass

    return app


class TestParseConfigPath:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, None),
            ("", "."),
            (".", "."),
            ("missing/config.toml", "missing/config.toml"),
            ("/absolute/config.toml", "/absolute/config.toml"),
            ("relative/../config.toml", "relative/../config.toml"),
            ("~/config.toml", "~/config.toml"),
            ("  café 日本語.toml  ", "  café 日本語.toml  "),
        ],
    )
    def test_parses_without_filesystem_validation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str | None, expected: str | None
    ) -> None:
        monkeypatch.chdir(tmp_path)
        app = typer.Typer()
        received: list[ProjectConfigPath | None] = []

        @app.callback()
        def initialize(config: ConfigOption = None) -> None:
            received.append(config)

        @app.command()
        def show() -> None:
            pass

        arguments = [] if value is None else ["--config", value]
        result = CliRunner().invoke(app, [*arguments, "show"])

        assert result.exit_code == 0
        assert not result.output
        assert received == [None if expected is None else ProjectConfigPath(Path(expected))]


class TestParseProtocol:
    @pytest.mark.parametrize("option", ["-p", "--protocol"])
    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_parses_supported_values(self, protocol_app: typer.Typer, option: str, protocol: Protocol) -> None:
        result = CliRunner().invoke(protocol_app, [option, protocol.value, "show"])

        assert result.exit_code == 0
        assert result.stdout == f"{protocol.value}\n"
        assert not result.stderr

    def test_leaves_missing_protocol_unspecified(self, protocol_app: typer.Typer) -> None:
        result = CliRunner().invoke(protocol_app, ["show"])

        assert result.exit_code == 0
        assert result.stdout == "unspecified\n"
        assert not result.stderr

    @pytest.mark.parametrize("value", ["invalid", "HUMAN", " llm", "llm ", "", "{protocol}", "{"])
    @pytest.mark.parametrize("prefix", [[], ["-p", "automation"]])
    def test_invalid_value_uses_llm_cell_before_command_execution(
        self, protocol_app: typer.Typer, value: str, prefix: list[str]
    ) -> None:
        result = CliRunner().invoke(protocol_app, [*prefix, "--protocol", value, "show"])

        assert result.exit_code == 1
        assert not result.stdout
        assert result.stderr.startswith("--TEST-CELL ")
        assert result.stderr.count(" BEGIN--\n") == 1
        assert result.stderr.count(" END--\n") == 1
        assert "kind=error\n" in result.stderr
        assert "code=invalid_arguments\n" in result.stderr
        assert f"`{value}`" in result.stderr
        for protocol in Protocol:
            assert protocol.value in result.stderr

    @pytest.mark.parametrize("option", ["-p", "--protocol"])
    def test_missing_value_remains_a_framework_error(self, protocol_app: typer.Typer, option: str) -> None:
        result = CliRunner().invoke(protocol_app, [option])

        assert result.exit_code == 2
        assert not result.stdout
        assert option in result.stderr
        assert "--TEST-CELL " not in result.stderr

    def test_help_describes_shared_option(self, protocol_app: typer.Typer) -> None:
        result = CliRunner().invoke(protocol_app, ["--help"])

        assert result.exit_code == 0
        assert not result.stderr
        assert "--protocol" in result.stdout
        assert "-p" in result.stdout
        assert "PROTOCOL" in result.stdout
        for protocol in Protocol:
            assert protocol.value in result.stdout
        assert "skill" in result.stdout
