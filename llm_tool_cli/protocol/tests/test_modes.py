import pytest

from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.errors import UnsupportedFormatterMode
from llm_tool_cli.protocol.formatters.automation import Formatter as AutomationFormatter
from llm_tool_cli.protocol.formatters.human import Formatter as HumanFormatter
from llm_tool_cli.protocol.formatters.llm import Formatter as LLMFormatter
from llm_tool_cli.protocol.formatters.tests.make import cell
from llm_tool_cli.protocol.modes import get_cell_formatter


class TestGetCellFormatter:
    @pytest.mark.parametrize(
        ("mode", "formatter_class"),
        (
            (Protocol.human, HumanFormatter),
            (Protocol.llm, LLMFormatter),
            (Protocol.automation, AutomationFormatter),
        ),
    )
    def test_returns_formatter_for_supported_mode(self, mode: Protocol, formatter_class: type[object]) -> None:
        assert isinstance(get_cell_formatter(mode, tool_label="TOOL"), formatter_class)

    def test_unsupported_mode_raises_internal_error(self) -> None:
        with pytest.raises(UnsupportedFormatterMode) as error_info:
            get_cell_formatter("missing", tool_label="TOOL")  # type: ignore[arg-type]

        assert error_info.value.details == {"mode": "missing"}

    @pytest.mark.parametrize("mode", [Protocol.human, Protocol.llm])
    @pytest.mark.parametrize("tool_label", ["TOOL", "OtherTool"])
    def test_passes_tool_label_to_text_formatter(self, mode: Protocol, tool_label: str) -> None:
        formatter = get_cell_formatter(mode, tool_label=tool_label)

        output = formatter.format_cell(cell(media_type=None, content=None, meta={})).decode()

        if mode == Protocol.human:
            assert output == f"----- {tool_label} CELL EjRWeBI0VniSNFZ4EjRWeA -----\nkind = sample_status\n\n"
        else:
            assert output == (
                f"--{tool_label}-CELL EjRWeBI0VniSNFZ4EjRWeA BEGIN--\n"
                "kind=sample_status\n"
                f"--{tool_label}-CELL EjRWeBI0VniSNFZ4EjRWeA END--\n"
            )

    def test_tool_label_does_not_change_automation_records(self) -> None:
        source = cell()

        first = get_cell_formatter(Protocol.automation, tool_label="FIRST").format_cell(source)
        second = get_cell_formatter(Protocol.automation, tool_label="SECOND").format_cell(source)

        assert first == second
