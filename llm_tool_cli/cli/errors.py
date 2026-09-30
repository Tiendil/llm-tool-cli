from typing import ClassVar

from llm_tool_cli.core import errors as core_errors
from llm_tool_cli.core.entities import ExitCode


class EnvironmentError(core_errors.EnvironmentError):
    """An expected command-line input failure."""


class InvalidArguments(EnvironmentError):
    cli_exit_code: ClassVar[ExitCode] = ExitCode.invalid_arguments
    code: str = "invalid_arguments"
    message: str = "{error.reason}"
    reason: str
