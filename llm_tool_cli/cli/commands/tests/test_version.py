import json
import re
from importlib import metadata
from pathlib import Path

import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.commands.version import register_version_command
from llm_tool_cli.cli.context import set_global_options
from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.cli.options import ConfigOption, ProtocolOption
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings

__all__ = ["isolated_settings"]


@pytest.fixture
def version_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_settings: None) -> typer.Typer:
    initialize(tool_label=ToolLabel("TEST"))
    distribution = tmp_path / "sample_distribution-9.8.7.dist-info"
    distribution.mkdir()
    (distribution / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: sample-distribution\nVersion: 9.8.7\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.chdir(tmp_path)
    app = create_app(help="Inspect the test package version.")

    @app.callback()
    def root(context: typer.Context, protocol: ProtocolOption = None, config: ConfigOption = None) -> None:
        set_global_options(context, GlobalOptions(protocol=protocol, config_path=config))

    register_version_command(app, distribution="sample-distribution")
    return app


class TestRegisterVersionCommand:
    @pytest.mark.parametrize("protocol", [None, "human", "llm", "automation"])
    def test_installed_version_and_protocol(self, version_app: typer.Typer, protocol: str | None) -> None:
        options = [] if protocol is None else ["-p", protocol]

        result = CliRunner().invoke(version_app, [*options, "version"])

        assert result.exit_code == 0
        assert not result.stderr
        if protocol == "automation":
            record = json.loads(result.stdout)
            assert record.pop("id")
            assert record == {"type": "version", "version": "9.8.7", "content": None}
        else:
            output = re.sub(r"[A-Za-z0-9_-]{22}", "<id>", result.stdout)
            if protocol == "llm":
                assert output == (
                    "--TEST-CELL <id> BEGIN--\nkind=version\ntype=version\nversion=9.8.7\n" "--TEST-CELL <id> END--\n"
                )
            else:
                assert output == "----- TEST CELL <id> -----\nkind = version\ntype = version\nversion = 9.8.7\n\n"

    @pytest.mark.parametrize("config_kind", ["missing", "invalid", "directory"])
    def test_ignores_configuration(self, version_app: typer.Typer, tmp_path: Path, config_kind: str) -> None:
        config = tmp_path / "config.toml"
        if config_kind == "invalid":
            config.write_text("not valid TOML", encoding="utf-8")
        elif config_kind == "directory":
            config.mkdir()

        result = CliRunner().invoke(version_app, ["--config", str(config), "-p", "automation", "version"])

        assert result.exit_code == 0
        assert not result.stderr
        assert json.loads(result.stdout)["version"] == "9.8.7"

    @pytest.mark.parametrize(
        "failure", [metadata.PackageNotFoundError("sample-distribution"), RuntimeError("lookup failed")]
    )
    def test_metadata_failure_propagates(
        self, version_app: typer.Typer, mocker: MockerFixture, failure: Exception
    ) -> None:
        mocker.patch("llm_tool_cli.cli.commands.version.metadata.version", side_effect=failure)

        result = CliRunner().invoke(version_app, ["-p", "automation", "version"])

        assert result.exit_code != 0
        assert isinstance(result.exception, type(failure))
        assert not result.stdout
        assert not result.stderr

    def test_registration_and_help_do_not_lookup_metadata(
        self, version_app: typer.Typer, mocker: MockerFixture
    ) -> None:
        lookup = mocker.patch("llm_tool_cli.cli.commands.version.metadata.version", side_effect=RuntimeError)
        app = create_app(help="An uninstalled package.")
        register_version_command(app, distribution="uninstalled-distribution")

        result = CliRunner().invoke(version_app, ["version", "-h"])

        assert result.exit_code == 0
        assert not result.stderr
        assert "Print the installed package version." in result.stdout
        lookup.assert_not_called()
