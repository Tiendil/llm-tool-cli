from pathlib import Path
from typing import Literal

import pydantic
import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.config import errors
from llm_tool_cli.config.project import (
    ProjectConfig,
    _load_project_config,
    initialize_project,
    load_project,
    project_config,
)
from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.config.tests.fixtures import project_static_settings
from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.core.errors import EnvironmentErrors
from llm_tool_cli.core.result import Err, Ok, UnwrapError
from llm_tool_cli.core.settings import ConfigFilename, StaticConfig, ToolLabel, static_config
from llm_tool_cli.paths import PathInput, ProjectConfigPath
from llm_tool_cli.paths.errors import InvalidProjectPath
from llm_tool_cli.protocol import Protocol

__all__ = ["project_static_settings"]

pytestmark = pytest.mark.usefixtures("project_static_settings")


class ApplicationConfig(BaseEntity):
    version: Literal[1] = 1
    count: int = 0


class TestProjectConfig:
    def test_project_dir__derives_from_configuration_path(self) -> None:
        config = ProjectConfig(config_path=ProjectConfigPath(Path("/project/custom.toml")))

        assert config.project_dir == Path("/project")

    @pytest.mark.parametrize("path", ["~/config.toml", "relative.toml"])
    def test_validate_config_path__rejects_unresolved_inputs(self, path: str) -> None:
        with pytest.raises(pydantic.ValidationError):
            ProjectConfig(config_path=ProjectConfigPath(Path(path)))


class TestLoadProject:
    def test_discovers_nearest_configuration_and_restores_scope(self, tmp_path: Path) -> None:
        (tmp_path / "tool.toml").write_text("count = 1", encoding="utf-8")
        project = tmp_path / "project"
        nested = project / "nested"
        nested.mkdir(parents=True)
        path = project / "tool.toml"
        path.write_text("count = 2", encoding="utf-8")

        scope = load_project(ApplicationConfig, cwd=PathInput(nested))
        assert not project_config.is_set()
        with scope as result:
            assert result.unwrap().count == 2
            assert project_config.get().config_path == path
            assert project_config.get().project_dir == project
            assert not runtime_config.is_set()
        assert not project_config.is_set()

    def test_uses_static_filename(self, tmp_path: Path) -> None:
        (tmp_path / "custom.toml").write_text("count = 3", encoding="utf-8")
        settings = StaticConfig(tool_label=ToolLabel("TEST"), config_filename=ConfigFilename("custom.toml"))
        with static_config.scope(settings), load_project(ApplicationConfig, cwd=PathInput(tmp_path)) as result:
            assert result.unwrap().count == 3
            assert project_config.get().config_path == tmp_path / "custom.toml"

    @pytest.mark.parametrize("explicit", [False, True])
    def test_rejects_config_symlink_without_binding_project(self, tmp_path: Path, explicit: bool) -> None:
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        target = target_dir / "actual.toml"
        target.write_text("count = 4", encoding="utf-8")
        link = tmp_path / "tool.toml"
        link.symlink_to(target)
        path = ProjectConfigPath(Path("tool.toml")) if explicit else None

        with load_project(ApplicationConfig, cwd=PathInput(tmp_path), path=path) as result:
            assert result.unwrap_err() == [InvalidProjectPath(path=str(link))]
            assert not project_config.is_set()

    @pytest.mark.parametrize("explicit", [False, True])
    def test_directory_alias_selects_resolved_project(self, tmp_path: Path, explicit: bool) -> None:
        root = tmp_path / "project"
        root.mkdir()
        (root / "tool.toml").write_text("count = 4", encoding="utf-8")
        alias = tmp_path / "alias"
        alias.symlink_to(root, target_is_directory=True)

        with load_project(
            ApplicationConfig,
            cwd=PathInput(alias),
            path=ProjectConfigPath(alias / "tool.toml") if explicit else None,
        ) as result:
            assert result.unwrap().count == 4
            assert project_config.get().config_path == root / "tool.toml"
            assert project_config.get().project_dir == root

    def test_missing_explicit_path_does_not_fall_back(self, tmp_path: Path) -> None:
        (tmp_path / "tool.toml").write_text("", encoding="utf-8")
        with load_project(
            ApplicationConfig, cwd=PathInput(tmp_path), path=ProjectConfigPath(Path("missing.toml"))
        ) as result:
            error = result.unwrap_err()[0]
            assert isinstance(error, errors.Unreadable)
            assert error.path == tmp_path / "missing.toml"
            assert not project_config.is_set()

    def test_missing_discovered_configuration(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch("llm_tool_cli.config.files.find_config", return_value=Ok(None))
        with load_project(ApplicationConfig, cwd=PathInput(tmp_path)) as result:
            error = result.unwrap_err()[0]
            assert isinstance(error, errors.NotFound)
            assert error.path == tmp_path
            assert "tool.toml" in error.reason
            assert not project_config.is_set()

    def test_missing_static_filename_is_internal_misuse(self, tmp_path: Path) -> None:
        with static_config.scope(StaticConfig(tool_label=ToolLabel("TEST"))):
            with pytest.raises(errors.ConfigFilenameNotSet):
                with load_project(ApplicationConfig, cwd=PathInput(tmp_path)):
                    pytest.fail("Project setup must reject missing application metadata.")
        assert not project_config.is_set()


class TestInitializeProject:
    @pytest.mark.parametrize("explicit", [False, True])
    def test_creates_validates_and_scopes_without_discovery(
        self, mocker: MockerFixture, tmp_path: Path, explicit: bool
    ) -> None:
        package = tmp_path / "package"
        (package / "fixtures").mkdir(parents=True)
        text = "version = 1\ncount = 5\n"
        (package / "fixtures/starter.toml").write_text(text, encoding="utf-8")
        mocker.patch("llm_tool_cli.config.files.importlib.resources.files", return_value=package)
        (tmp_path / "tool.toml").write_text("count = 9", encoding="utf-8")
        child = tmp_path / "child"
        child.mkdir()
        path = ProjectConfigPath(Path("custom.toml")) if explicit else None
        created = child / ("custom.toml" if explicit else "tool.toml")

        scope = initialize_project(
            ApplicationConfig, package="test", template="starter.toml", cwd=PathInput(child), path=path
        )
        assert not created.exists()
        with scope as result:
            assert result.unwrap().count == 5
            assert created.read_text(encoding="utf-8") == text
            assert project_config.get().config_path == created
            assert project_config.get().project_dir == child
        assert not project_config.is_set()

    @pytest.mark.parametrize(
        "text, error_type", [("version =", errors.InvalidToml), ("version = 2", errors.ValidationFailed)]
    )
    def test_invalid_starter_remains_on_disk_without_binding(
        self, mocker: MockerFixture, tmp_path: Path, text: str, error_type: type[errors.EnvironmentError]
    ) -> None:
        package = tmp_path / "package"
        (package / "fixtures").mkdir(parents=True)
        (package / "fixtures/starter.toml").write_text(text, encoding="utf-8")
        mocker.patch("llm_tool_cli.config.files.importlib.resources.files", return_value=package)
        with initialize_project(
            ApplicationConfig, package="test", template="starter.toml", cwd=PathInput(tmp_path)
        ) as result:
            assert isinstance(result.unwrap_err()[0], error_type)
            assert (tmp_path / "tool.toml").read_text(encoding="utf-8") == text
            assert not project_config.is_set()

    def test_creation_failure_skips_loading_and_preserves_binding(self, mocker: MockerFixture, tmp_path: Path) -> None:
        failure = errors.Unwritable(path=tmp_path / "tool.toml", reason="denied")
        mocker.patch("llm_tool_cli.config.project.initialize_config", return_value=Err([failure]))
        loading = mocker.patch("llm_tool_cli.config.project.load_config")
        previous = ProjectConfig(config_path=ProjectConfigPath(tmp_path / "active.toml"))
        with project_config.scope(previous):
            with initialize_project(
                ApplicationConfig, package="test", template="starter.toml", cwd=PathInput(tmp_path)
            ) as result:
                assert result.unwrap_err() == [failure]
                assert project_config.get() == previous
            assert project_config.get() == previous
        loading.assert_not_called()

    def test_missing_static_filename_is_internal_misuse(self, tmp_path: Path) -> None:
        with static_config.scope(StaticConfig(tool_label=ToolLabel("TEST"))):
            with pytest.raises(errors.ConfigFilenameNotSet):
                with initialize_project(
                    ApplicationConfig, package="test", template="starter.toml", cwd=PathInput(tmp_path)
                ):
                    pytest.fail("Project setup must reject missing application metadata.")
        assert not list(tmp_path.iterdir())


class TestLoadProjectConfig:
    @pytest.mark.parametrize("failure", [None, RuntimeError("body failed"), UnwrapError(error=[])])
    def test_restores_previous_binding_after_success_and_body_failures(
        self, tmp_path: Path, failure: Exception | None
    ) -> None:
        path = ProjectConfigPath(tmp_path / "tool.toml")
        path.write_text("count = 7", encoding="utf-8")
        previous = ProjectConfig(config_path=ProjectConfigPath(tmp_path / "outer.toml"))
        with project_config.scope(previous), runtime_config.scope(RuntimeConfig(protocol=Protocol.llm)):
            try:
                with _load_project_config(Ok(path), ApplicationConfig) as result:
                    assert result.unwrap().count == 7
                    assert project_config.get().config_path == path
                    assert runtime_config.get().protocol == Protocol.llm
                    if failure is not None:
                        raise failure
            except Exception as caught:
                assert caught == failure
            else:
                assert failure is None
            assert project_config.get() == previous

    def test_selection_failure_is_preserved_without_loading(self, mocker: MockerFixture, tmp_path: Path) -> None:
        failures: EnvironmentErrors = [
            errors.DiscoveryFailed(path=tmp_path, reason="denied"),
            errors.NotFound(path=tmp_path, reason="missing"),
        ]
        loading = mocker.patch("llm_tool_cli.config.project.load_config")
        with _load_project_config(Err(failures), ApplicationConfig) as result:
            assert result.unwrap_err() == failures
            assert not project_config.is_set()
        loading.assert_not_called()

    @pytest.mark.parametrize(
        "content, error_type",
        [
            (b"count =", errors.InvalidToml),
            (b"\xff", errors.InvalidEncoding),
            (b"version = 2", errors.ValidationFailed),
        ],
    )
    def test_loading_failure_preserves_previous_project(
        self, tmp_path: Path, content: bytes, error_type: type[errors.EnvironmentError]
    ) -> None:
        path = ProjectConfigPath(tmp_path / "tool.toml")
        path.write_bytes(content)
        previous = ProjectConfig(config_path=ProjectConfigPath(tmp_path / "active.toml"))
        with project_config.scope(previous), _load_project_config(Ok(path), ApplicationConfig) as result:
            assert isinstance(result.unwrap_err()[0], error_type)
            assert project_config.get() == previous

    def test_unexpected_loading_failure_propagates(self, mocker: MockerFixture, tmp_path: Path) -> None:
        failure = RuntimeError("unexpected schema defect")
        mocker.patch("llm_tool_cli.config.project.load_config", side_effect=failure)
        with pytest.raises(RuntimeError) as caught:
            with _load_project_config(Ok(ProjectConfigPath(tmp_path / "tool.toml")), ApplicationConfig):
                pytest.fail("Loading must fail before entering the project.")
        assert caught.value == failure
        assert not project_config.is_set()
