"""Reusable fields for application-owned configuration schemas."""

from typing import Annotated

import pydantic

from llm_tool_cli.paths import RelativeProjectPath


def _validate_config_version(value: object, handler: pydantic.ValidatorFunctionWrapHandler) -> object:
    """Require an integer and explain failures of the application's version constraint."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Configuration version must be an integer; received {value!r}.")

    try:
        return handler(value)
    except pydantic.ValidationError as error:
        failures = error.errors()
        if len(failures) != 1 or failures[0]["type"] != "literal_error":
            raise
        supported = failures[0]["ctx"]["expected"]
        raise ValueError(f"Unsupported configuration version {value}; supported version: {supported}.") from error


type ConfigVersion[Version: int] = Annotated[Version, pydantic.WrapValidator(_validate_config_version)]


def validate_relative_project_path(path: RelativeProjectPath) -> RelativeProjectPath:
    """Pydantic validator for project-relative paths without parent references."""
    if path.is_absolute():
        raise ValueError("Project paths must be relative to the project root.")

    if any(part == ".." for part in path.parts):
        raise ValueError("Project paths must not contain parent-directory references.")

    return path


type SessionDir = Annotated[RelativeProjectPath, pydantic.AfterValidator(validate_relative_project_path)]
