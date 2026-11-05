import re
from enum import IntEnum
from typing import Self

import pydantic
from pydantic_core import core_schema


class ExitCode(IntEnum):
    success = 0
    invalid_arguments = 1
    configuration_error = 2
    environment_error = 3


class BaseEntity(pydantic.BaseModel):
    """Shared validation, copying, and JSON serialization for structured values."""

    model_config = pydantic.ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        from_attributes=False,
    )

    def replace(self, **changes: object) -> Self:
        """Return a deep copy with trusted changes applied without validation."""
        return self.model_copy(update=changes, deep=True)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_data: str) -> Self:
        return cls.model_validate_json(json_data)


class Slug(str):
    """A trimmed identifier of lowercase ASCII words separated by single hyphens."""

    __slots__ = ()

    def __new__(cls, value: str) -> Self:
        """Strip outer whitespace, then validate without rewriting the identifier."""
        value = value.strip()
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is None:
            raise ValueError("A slug must contain lowercase ASCII letters or digits separated by single hyphens.")
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: object, handler: pydantic.GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(str))


class ToolName(Slug):
    """One canonical name shared by application identity, storage, and output."""

    __slots__ = ()
