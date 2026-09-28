from abc import ABC, abstractmethod

from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.protocol.cells import Cell


class Formatter(ABC):
    __slots__ = ()

    def format_error(self, error: EnvironmentError) -> bytes:
        return f"{error.format_message()}\n".encode()

    @abstractmethod
    def format_cell(self, cell: Cell) -> bytes: ...  # noqa: E704
