from typing import Self

import pydantic

from llm_tool_cli.protocol.errors import ContentWithoutMediaType
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells import AutomationOutputCell, HumanOutputCell, LLMOutputCell
from llm_tool_cli.protocol.output_cells.base import MetaValue, OutputCell


class ContentCell(LogicCell):
    """Prepared content and metadata shared by all output protocols."""

    kind: str
    media_type: str | None = None
    content: str | None = None
    meta: dict[str, MetaValue] = pydantic.Field(default_factory=dict)

    @pydantic.model_validator(mode="after")
    def validate_content(self) -> Self:
        if self.media_type is None and self.content is not None:
            raise ContentWithoutMediaType()
        return self

    def render_human(self) -> list[OutputCell]:
        return self._render(HumanOutputCell)

    def render_llm(self) -> list[OutputCell]:
        return self._render(LLMOutputCell)

    def render_automation(self) -> list[OutputCell]:
        return self._render(AutomationOutputCell)

    def _render(self, cell_type: type[OutputCell]) -> list[OutputCell]:
        return [cell_type(kind=self.kind, media_type=self.media_type, content=self.content, meta=self.meta)]
