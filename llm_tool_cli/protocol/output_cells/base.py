import base64
import uuid
from abc import ABC, abstractmethod
from typing import Self

import pydantic

from llm_tool_cli.core.entities import BaseEntity

MetaValue = str | int | bool | None | list[str]


def to_meta_value(value: object) -> MetaValue:
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value

    return str(value)


class RenderContext(BaseEntity):
    model_config = pydantic.ConfigDict(str_strip_whitespace=False)

    index: int = pydantic.Field(ge=0)
    total: int = pydantic.Field(ge=1)
    tool_label: str

    @pydantic.model_validator(mode="after")
    def validate_position(self) -> Self:
        if self.index >= self.total:
            raise ValueError("Cell index must be smaller than the sequence size")
        return self


class OutputCell(BaseEntity, ABC):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    kind: str
    media_type: str | None
    content: str | None
    meta: dict[str, MetaValue] = pydantic.Field(default_factory=dict)

    @classmethod
    def build(cls, kind: str, media_type: str | None, content: str | None, **meta: MetaValue) -> Self:
        if media_type is None and content is not None:
            from llm_tool_cli.protocol.errors import ContentWithoutMediaType

            raise ContentWithoutMediaType()

        return cls(kind=kind, media_type=media_type, content=content, meta=meta)

    @classmethod
    def build_meta(cls, kind: str, **meta: MetaValue) -> Self:
        return cls.build(kind=kind, media_type=None, content=None, **meta)

    @classmethod
    def build_markdown(cls, kind: str, content: str, **meta: MetaValue) -> Self:
        return cls.build(kind=kind, media_type="text/markdown", content=content, **meta)

    @property
    def short_id(self) -> str:
        return base64.urlsafe_b64encode(self.id.bytes).rstrip(b"=").decode()

    @abstractmethod
    def render(self, context: RenderContext) -> bytes: ...  # noqa: E704
