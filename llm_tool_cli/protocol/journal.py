import datetime

import pydantic

from llm_tool_cli.core.entities import BaseEntity


class JournalRecord(BaseEntity):
    """Protocol-independent journal data, ready for an external processor."""

    message: str
    timestamp: datetime.datetime = pydantic.Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    actor_id: str | None = None
    attributes: dict[str, pydantic.JsonValue] = pydantic.Field(default_factory=dict)

    def as_dict(self) -> dict[str, pydantic.JsonValue]:
        """Flatten attributes without allowing them to replace common fields."""
        fields = self.model_dump(mode="json")
        attributes = fields.pop("attributes")
        fields["timestamp"] = self.timestamp.isoformat()
        return {**attributes, **fields}
