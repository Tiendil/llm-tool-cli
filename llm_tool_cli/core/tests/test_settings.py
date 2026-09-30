import pytest

from llm_tool_cli.core.errors import ToolLabelAlreadyInitialized, ToolLabelNotInitialized
from llm_tool_cli.core.settings import ToolLabel, get_tool_label, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings

__all__ = ["isolated_settings"]

pytestmark = pytest.mark.usefixtures("isolated_settings")


class TestInitialize:
    @pytest.mark.parametrize("label", ["TOOL", "", "  café 日本語  "])
    def test_installs_exact_label(self, label: str) -> None:
        initialize(tool_label=ToolLabel(label))

        assert get_tool_label() == label

    def test_same_label_is_idempotent(self) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        initialize(tool_label=ToolLabel("TOOL"))

        assert get_tool_label() == "TOOL"

    def test_conflicting_label_preserves_original(self) -> None:
        initialize(tool_label=ToolLabel(""))

        with pytest.raises(ToolLabelAlreadyInitialized) as caught:
            initialize(tool_label=ToolLabel("OTHER"))

        assert caught.value.details == {"current": "", "requested": "OTHER"}
        assert get_tool_label() == ""


class TestGetToolLabel:
    def test_missing_initialization(self) -> None:
        with pytest.raises(ToolLabelNotInitialized):
            get_tool_label()

    def test_returns_installed_label(self) -> None:
        initialize(tool_label=ToolLabel("TOOL"))

        assert get_tool_label() == "TOOL"
