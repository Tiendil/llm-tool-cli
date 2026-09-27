"""Internal failures in output protocol construction."""

from typing import ClassVar

from llm_tool_cli.core import errors as core_errors


class InternalError(core_errors.InternalError):
    """Base for internal output protocol failures."""


class ContentWithoutMediaType(InternalError):
    message_template: ClassVar[str] = "Cannot set content when media_type is None."
