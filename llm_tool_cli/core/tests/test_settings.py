from contextvars import Context

import pytest

from llm_tool_cli.core import settings
from llm_tool_cli.core.errors import ContextValueNotSet, ToolLabelAlreadyInitialized
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


class TestInitialize:
    @pytest.mark.parametrize("label", ["TOOL", "", "  café 日本語  "])
    def test_installs_exact_label(self, label: str) -> None:
        initialize(label=ToolLabel(label))

        assert settings.tool_label.get() == label

    def test_same_label_is_idempotent(self) -> None:
        initialize(label=ToolLabel("TOOL"))
        initialize(label=ToolLabel("TOOL"))

        assert settings.tool_label.get() == "TOOL"

    def test_conflicting_label_preserves_original(self) -> None:
        initialize(label=ToolLabel(""))

        with pytest.raises(ToolLabelAlreadyInitialized) as caught:
            initialize(label=ToolLabel("OTHER"))

        assert caught.value.details == {"current": "", "requested": "OTHER"}
        assert settings.tool_label.get() == ""

    def test_initialization_uses_current_execution_context(self) -> None:
        initialize(label=ToolLabel("OUTER"))
        execution = Context()

        with pytest.raises(ContextValueNotSet) as caught:
            execution.run(settings.tool_label.get)

        assert caught.value.details == {"name": "tool_label"}
        execution.run(initialize, label=ToolLabel("INNER"))

        assert execution.run(settings.tool_label.get) == "INNER"
        assert settings.tool_label.get() == "OUTER"
