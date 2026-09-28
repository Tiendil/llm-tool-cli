from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.errors import UnsupportedFormatterMode
from llm_tool_cli.protocol.formatters.automation import Formatter as AutomationFormatter
from llm_tool_cli.protocol.formatters.base import Formatter
from llm_tool_cli.protocol.formatters.human import Formatter as HumanFormatter
from llm_tool_cli.protocol.formatters.llm import Formatter as LLMFormatter


def get_cell_formatter(mode: Protocol, *, tool_label: str) -> Formatter:
    match mode:
        case Protocol.human:
            return HumanFormatter(tool_label=tool_label)
        case Protocol.llm:
            return LLMFormatter(tool_label=tool_label)
        case Protocol.automation:
            return AutomationFormatter()
        case _:
            raise UnsupportedFormatterMode(details={"mode": mode})
