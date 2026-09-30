from typing import Self

import pydantic

from llm_tool_cli.protocol.errors import ContentWithoutMediaType
from llm_tool_cli.protocol.logic_cells.uniform import UniformCell
from llm_tool_cli.protocol.output_cells.base import MetaValue, OutputCell


class ContentCell(UniformCell):
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

    def _render(self, cell_type: type[OutputCell]) -> OutputCell:
        return cell_type(kind=self.kind, media_type=self.media_type, content=self.content, meta=self.meta)
