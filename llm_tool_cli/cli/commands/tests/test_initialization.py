import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

import pydantic
import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.commands.initialization import InitOperationScope, register_init_command
from llm_tool_cli.config import errors as config_errors
from llm_tool_cli.config.project import project_config
from llm_tool_cli.config.runtime import runtime_config
from llm_tool_cli.config.tests.fixtures import project_static_settings
from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.output import StreamOutputEmitter, output
from llm_tool_cli.paths import PathInput, ProjectConfigPath
from llm_tool_cli.protocol.tests.helpers import cell_payloads

__all__ = ["project_static_settings"]

pytestmark = pytest.mark.usefixtures("project_static_settings")


class ApplicationConfig(pydantic.BaseModel):
    count: int


@pytest.fixture
def init_app_factory(
    tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> Callable[[InitOperationScope | None], typer.Typer]:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "starter.toml").write_text("count = 5\n", encoding="utf-8")
    mocker.patch("llm_tool_cli.config.files.importlib.resources.files", return_value=tmp_path)
    monkeypatch.chdir(tmp_path)

    def create(operation_scope: InitOperationScope | None) -> typer.Typer:
        app = create_app(help="Initialize a test project.")
        register_init_command(
            app,
            config_class=ApplicationConfig,
            package="test_resources",
            template="starter.toml",
            operation_scope=operation_scope,
        )
        return app

    return create


@pytest.fixture
def init_app(init_app_factory: Callable[[InitOperationScope | None], typer.Typer]) -> typer.Typer:
    return init_app_factory(None)


class TestRegisterInitCommand:
    @pytest.mark.parametrize("explicit", [False, True])
    def test_operation_scope_selects_target_and_survives_output(
        self,
        init_app_factory: Callable[[InitOperationScope | None], typer.Typer],
        tmp_path: Path,
        explicit: bool,
    ) -> None:
        selected = ProjectConfigPath(tmp_path / "selected.toml")
        events: list[str] = []

        class ScopedStream(StringIO):
            def write(self, value: str) -> int:
                assert events == ["entered"]
                assert project_config.get().config_path == selected
                assert selected.read_text(encoding="utf-8") == "count = 5\n"
                return super().write(value)

        stream = ScopedStream()

        @contextmanager
        def scope(cwd: PathInput, path: ProjectConfigPath | None) -> Iterator[Result[ProjectConfigPath]]:
            assert cwd == tmp_path
            assert path == (Path("requested.toml") if explicit else None)
            assert not selected.exists()
            assert not project_config.is_set()
            events.append("entered")
            with output.scope(StreamOutputEmitter(stream=stream)):
                try:
                    yield Ok(selected)
                finally:
                    events.append("released")

        app = init_app_factory(scope)
        assert not events
        arguments = ["-p", "automation"]
        if explicit:
            arguments.extend(["--config", "requested.toml"])

        result = CliRunner().invoke(app, [*arguments, "init"])

        assert result.exit_code == 0, result.exception
        assert events == ["entered", "released"]
        assert json.loads(stream.getvalue())["path"] == str(selected)
        assert not (tmp_path / "tool.toml").exists()
        assert not (tmp_path / "requested.toml").exists()
        assert not result.stdout
        assert not result.stderr
        assert not project_config.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()

    def test_failed_operation_scope_prevents_creation(
        self, init_app_factory: Callable[[InitOperationScope | None], typer.Typer], tmp_path: Path
    ) -> None:
        selected = ProjectConfigPath(tmp_path / "tool.toml")
        error = config_errors.Unwritable(path=selected, reason="Access denied by the application")
        events: list[str] = []

        @contextmanager
        def scope(cwd: PathInput, path: ProjectConfigPath | None) -> Iterator[Result[ProjectConfigPath]]:
            events.append("entered")
            try:
                yield Err([error])
            finally:
                events.append("released")

        result = CliRunner().invoke(init_app_factory(scope), ["-p", "automation", "init"])

        assert result.exit_code == 2
        record = json.loads(result.stdout)
        assert record["code"] == error.code
        assert record["path"] == str(selected)
        assert record["reason"] == error.reason
        assert events == ["entered", "released"]
        assert not selected.exists()
        assert not result.stderr
        assert not project_config.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()

    @pytest.mark.parametrize("unexpected", [False, True])
    def test_operation_scope_releases_after_initialization_failure(
        self,
        init_app_factory: Callable[[InitOperationScope | None], typer.Typer],
        tmp_path: Path,
        mocker: MockerFixture,
        unexpected: bool,
    ) -> None:
        selected = ProjectConfigPath(tmp_path / "tool.toml")
        events: list[str] = []
        failure = RuntimeError("Unexpected initialization failure")
        if unexpected:
            mocker.patch("llm_tool_cli.config.project.initialize_config", side_effect=failure)
        else:
            (tmp_path / "fixtures/starter.toml").write_text("count =", encoding="utf-8")

        @contextmanager
        def scope(cwd: PathInput, path: ProjectConfigPath | None) -> Iterator[Result[ProjectConfigPath]]:
            events.append("entered")
            try:
                yield Ok(selected)
            finally:
                events.append("released")

        result = CliRunner().invoke(init_app_factory(scope), ["-p", "automation", "init"])

        assert events == ["entered", "released"]
        if unexpected:
            assert result.exception == failure
            assert not result.stdout
            assert not selected.exists()
        else:
            assert result.exit_code == 2
            assert json.loads(result.stdout)["code"] == "config_invalid_toml"
            assert selected.read_text(encoding="utf-8") == "count ="
        assert not result.stderr
        assert not project_config.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()

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
        operation_scope = mocker.Mock(side_effect=RuntimeError)
        app = create_app(help="Initialize a project.")
        register_init_command(
            app,
            config_class=ApplicationConfig,
            package="unavailable_resources",
            template="missing.toml",
            help="Create the application configuration.",
            operation_scope=operation_scope,
        )

        result = CliRunner().invoke(app, ["init", "-h"])

        assert result.exit_code == 0
        assert "Create the application configuration." in result.stdout
        assert not result.stderr
        assert not project_config.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()
        prepare.assert_not_called()
        operation_scope.assert_not_called()
