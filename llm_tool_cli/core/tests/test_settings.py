from contextvars import Context

import pydantic
import pytest

from llm_tool_cli.core import settings
from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.core.errors import ContextValueAlreadySet, ContextValueNotSet
from llm_tool_cli.core.settings import ConfigFilename, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


class TestInitialize:
    @pytest.mark.parametrize(("name", "expected"), [("tool", "tool"), ("  demo-tool-2  ", "demo-tool-2")])
    def test_installs_normalized_name(self, name: str, expected: str) -> None:
        initialize(name=ToolName(name))

        assert settings.static_config.get().tool_name == expected

    def test_same_name_is_idempotent(self) -> None:
        initialize(name=ToolName("tool"))
        initialize(name=ToolName(" tool "))

        assert settings.static_config.get().tool_name == "tool"

    def test_same_application_settings_are_idempotent(self) -> None:
        initialize(name=ToolName("tool"), config_filename=ConfigFilename("tool.toml"))
        initialize(name=ToolName("tool"), config_filename=ConfigFilename("tool.toml"))

        assert settings.static_config.get().config_filename == "tool.toml"

    @pytest.mark.parametrize("filename", [None, ConfigFilename("other.toml")])
    def test_conflicting_filename_preserves_original(self, filename: ConfigFilename | None) -> None:
        initialize(name=ToolName("tool"), config_filename=ConfigFilename("tool.toml"))

        with pytest.raises(ContextValueAlreadySet) as caught:
            initialize(name=ToolName("tool"), config_filename=filename)

        assert caught.value.details == {"name": "static_config"}
        assert settings.static_config.get().config_filename == "tool.toml"

    def test_conflicting_name_preserves_original(self) -> None:
        initialize(name=ToolName("tool"))

        with pytest.raises(ContextValueAlreadySet) as caught:
            initialize(name=ToolName("other"))

        assert caught.value.details == {"name": "static_config"}
        assert settings.static_config.get().tool_name == "tool"

    def test_initialization_uses_current_execution_context(self) -> None:
        initialize(name=ToolName("outer"))
        execution = Context()

        with pytest.raises(ContextValueNotSet) as caught:
            execution.run(settings.static_config.get)

        assert caught.value.details == {"name": "static_config"}
        execution.run(initialize, name=ToolName("inner"))

        assert execution.run(settings.static_config.get).tool_name == "inner"
        assert settings.static_config.get().tool_name == "outer"


class TestStaticConfig:
    def test_normalizes_identity_and_preserves_filename(self) -> None:
        value = settings.StaticConfig.model_validate({"tool_name": " sample ", "config_filename": " tool.toml "})
        assert isinstance(value.tool_name, ToolName)
        assert value.model_dump(mode="json") == {"tool_name": "sample", "config_filename": " tool.toml "}

    @pytest.mark.parametrize("name", ["", "Tool", "two words", "café", "tool_name", "tool--name", "a/b"])
    def test_rejects_names_outside_the_slug_contract(self, name: str) -> None:
        with pytest.raises(pydantic.ValidationError):
            settings.StaticConfig.model_validate({"tool_name": name})
