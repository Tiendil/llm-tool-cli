"""Public project-path failures."""

from llm_tool_cli.core import errors as core_errors


class EnvironmentError(core_errors.EnvironmentError):
    """Base for expected project-path failures."""


class InvalidProjectPath(EnvironmentError):
    """An input cannot identify a path below the project root."""

    code: str = "invalid_project_path"
    message: str = "invalid project path `{error.path}`"
    path: str


class PathResolutionFailed(EnvironmentError):
    """A filesystem path could not be resolved."""

    code: str = "path_resolution_failed"
    message: str = "could not resolve project path `{error.path}`: {error.reason}"
    path: str
    reason: str
