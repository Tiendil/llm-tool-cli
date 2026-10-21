import json
from pathlib import Path

import pydantic
import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.commands.initialization import register_init_command
from llm_tool_cli.config.project import project_config
from llm_tool_cli.config.runtime import runtime_config
from llm_tool_cli.config.tests.fixtures import project_static_settings
from llm_tool_cli.output import output
from llm_tool_cli.protocol.tests.helpers import cell_payloads

__all__ = ["project_static_settings"]

pytestmark = pytest.mark.usefixtures("project_static_settings")


class ApplicationConfig(pydantic.BaseModel):
    count: int


@pytest.fixture
def init_app(tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> typer.Typer:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "starter.toml").write_text("count = 5\n", encoding="utf-8")
    mocker.patch("llm_tool_cli.config.files.importlib.resources.files", return_value=tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app(help="Initialize a test project.")
    register_init_command(app, config_class=ApplicationConfig, package="test_resources", template="starter.toml")
    return app


class TestRegisterInitCommand:
    @pytest.mark.parametrize("protocol", [None, "human", "llm", "automation"])
    @pytest.mark.parametrize("explicit", [False, True])
    def test_creates_validated_config_and_reports_selected_path(
        self, init_app: typer.Typer, tmp_path: Path, protocol: str | None, explicit: bool
    ) -> None:
        options = [] if protocol is None else ["-p", protocol]
        if explicit:
            options.extend(["--config", "custom.toml"])
        path = tmp_path / ("custom.toml" if explicit else "tool.toml")

        result = CliRunner().invoke(init_app, [*options, "init"])

        assert result.exit_code == 0, result.exception
        assert path.read_text(encoding="utf-8") == "count = 5\n"
        assert not result.stderr
        if protocol == "automation":
            assert cell_payloads([json.loads(result.stdout)]) == [
                {"type": "operation_succeeded", "content": "Configuration created.", "path": str(path)}
            ]
        elif protocol == "llm":
            assert "type=operation_succeeded\n" in result.stdout
            assert f"path={path}\n" in result.stdout
        else:
            assert result.stdout == f"path: {path}\n\nConfiguration created.\n\n"
        assert not project_config.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()

    @pytest.mark.parametrize(
        "text, code", [("count =", "config_invalid_toml"), ('count = "invalid"', "config_validation_failed")]
    )
    def test_invalid_starter_keeps_file_and_reports_failure_without_success(
        self, init_app: typer.Typer, tmp_path: Path, text: str, code: str
    ) -> None:
        (tmp_path / "fixtures/starter.toml").write_text(text, encoding="utf-8")

        result = CliRunner().invoke(init_app, ["-p", "automation", "init"])

        assert result.exit_code == 2
        record = json.loads(result.stdout)
        assert record["type"] == "error"
        assert record["code"] == code
        assert (tmp_path / "tool.toml").read_text(encoding="utf-8") == text
        assert not result.stderr
        assert not project_config.is_set()

    def test_existing_file_is_preserved(self, init_app: typer.Typer, tmp_path: Path) -> None:
        path = tmp_path / "tool.toml"
        path.write_text("count = 9", encoding="utf-8")

        result = CliRunner().invoke(init_app, ["-p", "automation", "init"])

        assert result.exit_code == 2
        assert json.loads(result.stdout)["code"] == "config_already_exists"
        assert path.read_text(encoding="utf-8") == "count = 9"
        assert not result.stderr
        assert not project_config.is_set()

    def test_unexpected_failure_propagates(self, init_app: typer.Typer, mocker: MockerFixture) -> None:
        failure = RuntimeError("Unexpected creation failure")
        mocker.patch("llm_tool_cli.config.project.initialize_config", side_effect=failure)

        result = CliRunner().invoke(init_app, ["init"])

        assert result.exception == failure
        assert not result.stdout
        assert not result.stderr
        assert not project_config.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()

    def test_registration_and_help_do_not_prepare_project(self, mocker: MockerFixture) -> None:
        prepare = mocker.patch("llm_tool_cli.cli.commands.initialization.initialize_project", side_effect=RuntimeError)
        app = create_app(help="Initialize a project.")
        register_init_command(
            app,
            config_class=ApplicationConfig,
            package="unavailable_resources",
            template="missing.toml",
            help="Create the application configuration.",
        )

        result = CliRunner().invoke(app, ["init", "-h"])

        assert result.exit_code == 0
        assert "Create the application configuration." in result.stdout
        assert not result.stderr
        assert not project_config.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()
        prepare.assert_not_called()
