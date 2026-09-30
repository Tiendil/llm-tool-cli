from llm_tool_cli.core import errors as core_errors


class EnvironmentError(core_errors.EnvironmentError):
    """An expected command-line input failure."""


class InvalidProtocol(EnvironmentError):
    code: str = "invalid_arguments"
    message: str = "{error.reason}"
    reason: str
