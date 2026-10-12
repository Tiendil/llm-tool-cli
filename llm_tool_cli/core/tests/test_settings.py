from contextvars import Context

import pytest

from llm_tool_cli.core import settings
from llm_tool_cli.core.errors import ContextValueAlreadySet, ContextValueNotSet, ToolLabelAlreadyInitialized
from llm_tool_cli.core.settings import ConfigFilename, ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


class TestInitialize:
    @pytest.mark.parametrize("label", ["TOOL", "", "  café 日本語  "])
    def test_installs_exact_label(self, label: str) -> None:
        initialize(label=ToolLabel(label))

        assert settings.static_config.get().tool_label == label

    def test_same_label_is_idempotent(self) -> None:
        initialize(label=ToolLabel("TOOL"))
        initialize(label=ToolLabel("TOOL"))

        assert settings.static_config.get().tool_label == "TOOL"

    def test_same_application_settings_are_idempotent(self) -> None:
        initialize(label=ToolLabel("TOOL"), config_filename=ConfigFilename("tool.toml"))
        initialize(label=ToolLabel("TOOL"), config_filename=ConfigFilename("tool.toml"))

        assert settings.static_config.get().config_filename == "tool.toml"

    @pytest.mark.parametrize("filename", [None, ConfigFilename("other.toml")])
    def test_conflicting_filename_preserves_original(self, filename: ConfigFilename | None) -> None:
        initialize(label=ToolLabel("TOOL"), config_filename=ConfigFilename("tool.toml"))

        with pytest.raises(ContextValueAlreadySet) as caught:
            initialize(label=ToolLabel("TOOL"), config_filename=filename)

        assert caught.value.details == {"name": "static_config"}
        assert settings.static_config.get().config_filename == "tool.toml"

    def test_conflicting_label_preserves_original(self) -> None:
        initialize(label=ToolLabel(""))

        with pytest.raises(ToolLabelAlreadyInitialized) as caught:
            initialize(label=ToolLabel("OTHER"))

        assert caught.value.details == {"current": "", "requested": "OTHER"}
        assert settings.static_config.get().tool_label == ""

    def test_initialization_uses_current_execution_context(self) -> None:
        initialize(label=ToolLabel("OUTER"))
        execution = Context()

        with pytest.raises(ContextValueNotSet) as caught:
            execution.run(settings.static_config.get)

        assert caught.value.details == {"name": "static_config"}
        execution.run(initialize, label=ToolLabel("INNER"))

        assert execution.run(settings.static_config.get).tool_label == "INNER"
        assert settings.static_config.get().tool_label == "OUTER"
