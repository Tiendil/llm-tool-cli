from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from llm_tool_cli.cli.options import ConfigOption
from llm_tool_cli.paths import ProjectConfigPath


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
