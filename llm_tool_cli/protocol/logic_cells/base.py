from abc import ABC, abstractmethod
from typing import assert_never

from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.protocol.entities import Protocol
from llm_tool_cli.protocol.output_cells.base import OutputCell


class LogicCell(BaseEntity, ABC):
    """Application data projected into prepared output cells for a protocol."""

    def render(self, protocol: Protocol) -> list[OutputCell]:
        match protocol:
            case Protocol.human:
                return self.render_human()
            case Protocol.llm:
                return self.render_llm()
            case Protocol.automation:
                return self.render_automation()
            case _:
                assert_never(protocol)

    @abstractmethod
    def render_human(self) -> list[OutputCell]: ...  # noqa: E704

    @abstractmethod
    def render_llm(self) -> list[OutputCell]: ...  # noqa: E704

    @abstractmethod
    def render_automation(self) -> list[OutputCell]: ...  # noqa: E704
