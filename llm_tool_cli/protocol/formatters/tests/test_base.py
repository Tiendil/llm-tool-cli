import pytest

from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.protocol.formatters import Formatter
from llm_tool_cli.protocol.formatters.human import Formatter as HumanFormatter
from llm_tool_cli.protocol.formatters.llm import Formatter as LlmFormatter


class TestFormatter:
    @pytest.mark.parametrize("formatter", [HumanFormatter(tool_label="TOOL"), LlmFormatter(tool_label="TOOL")])
    def test_format_error__preserves_shared_message(self, formatter: Formatter) -> None:
        error = EnvironmentError(code="service", message="{error.code}: unavailable")

        assert formatter.format_error(error) == b"service: unavailable\n"
