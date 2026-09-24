from typing import Self

import pydantic


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
