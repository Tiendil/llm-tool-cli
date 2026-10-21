from llm_tool_cli.core.errors import EnvironmentError as BaseEnvironmentError


class EnvironmentError(BaseEnvironmentError):
    """Expected failures in output delivery."""


class JournalCommandConfigInvalid(EnvironmentError):
    code: str = "journal_command_config_invalid"
    message: str = "Journal command config is invalid: {error.details}"
    argument: str
    details: str


class JournalCommandFailed(EnvironmentError):
    code: str = "journal_command_failed"
    message: str = "Journal command failed: {error.details}"
    ways_to_fix: list[str] = ["Check the configured journal command and its arguments."]
    command: list[str]
    returncode: int | None
    details: str
