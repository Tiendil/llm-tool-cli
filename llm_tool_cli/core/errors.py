from collections.abc import Mapping
from typing import ClassVar, Self

import pydantic

from llm_tool_cli.core.entities import BaseEntity


class InternalError(Exception):
    """Base for internal and technical exceptions with structured context.

    Details are copied shallowly and may contain arbitrary debugging context or
    technical propagation payloads. They are not environment-error diagnostics.
    """

    message_template: ClassVar[str | None] = None

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.details: dict[str, object] = dict(details) if details is not None else {}
        if message is None and self.message_template is not None:
            message = self.message_template.format(**self.details)
        super().__init__(type(self).__name__ if message is None else message)

    @property
    def message(self) -> str:
        return super().__str__()


class EnvironmentError(BaseEntity):
    """An expected operational failure returned as data.

    Subclasses declare typed context fields. Messages and corrective guidance may
    reference those fields using ``{error.field}``.
    """

    code: str
    message: str
    ways_to_fix: list[str] = pydantic.Field(default_factory=list)
    _cause: Exception | None = pydantic.PrivateAttr(default=None)

    @property
    def cause(self) -> Exception | None:
        return self._cause

    def with_cause(self, cause: Exception) -> Self:
        """Attach the original failure at its translation boundary."""
        self._cause = cause
        return self

    def format_message(self) -> str:
        return self.message.format(error=self)

    def as_record(self) -> dict[str, object]:
        """Serialize typed context with the stable diagnostic record fields."""
        context = self.model_dump(mode="json", exclude={"code", "message", "ways_to_fix"})
        return {
            **context,
            "type": "error",
            "code": self.code,
            "message": self.format_message(),
        }


EnvironmentErrors = list[EnvironmentError]


class EnvironmentErrorsProxy(InternalError):
    """Carry environment errors through callbacks that cannot return results."""

    def __init__(self, errors: EnvironmentErrors) -> None:
        super().__init__(
            "This is a technical exception to pass an environment error up the call stack.",
            details={"errors": errors},
        )
