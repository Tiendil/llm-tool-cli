from pathlib import Path

from llm_tool_cli.core import errors as core_errors
from llm_tool_cli.core.entities import ToolName


class EnvironmentError(core_errors.EnvironmentError):
    pass


class StateDirectoryUnavailable(EnvironmentError):
    code: str = "state_directory_unavailable"
    message: str = "Cannot select the state directory for {error.tool_name}: {error.reason}"
    ways_to_fix: list[str] = ["Ensure the platform user-state location is available and absolute."]
    tool_name: ToolName
    path: Path | None = None
    reason: str
