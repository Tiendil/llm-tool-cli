"""Project preparation and scoped settings, independent of CLI frameworks."""

from collections.abc import Iterator
from contextlib import contextmanager

import pydantic

from llm_tool_cli.config import errors
from llm_tool_cli.config.files import initialize_config, load_config, locate_config
from llm_tool_cli.core import settings
from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.core.result import Err, Result
from llm_tool_cli.paths import PathInput, ProjectConfigPath, ProjectRootPath


class ProjectConfig(BaseEntity):
    config_path: ProjectConfigPath

    @pydantic.field_validator("config_path")
    @classmethod
    def validate_config_path(cls, value: ProjectConfigPath) -> ProjectConfigPath:
        if not value.is_absolute():
            raise ValueError("The active configuration path must be absolute.")
        return value

    @property
    def project_dir(self) -> ProjectRootPath:
        return ProjectRootPath(self.config_path.parent)


project_config = ContextValue[ProjectConfig]("project_config")


@contextmanager
def load_project[T: pydantic.BaseModel](
    config_class: type[T], *, cwd: PathInput, path: ProjectConfigPath | None = None
) -> Iterator[Result[T]]:
    """Select and validate a configuration, binding its project for the scope.

    Failures yield an error result without replacing the active project. The
    caller owns the scope's lifetime and application-specific configuration use.
    """
    filename = settings.static_config.get().config_filename
    if filename is None:
        raise errors.ConfigFilenameNotSet()
    selected = locate_config(filename, path=path, cwd=cwd)
    with _load_project_config(selected, config_class) as result:
        yield result


@contextmanager
def initialize_project[T: pydantic.BaseModel](
    config_class: type[T],
    *,
    package: str,
    template: str,
    cwd: PathInput,
    path: ProjectConfigPath | None = None,
) -> Iterator[Result[T]]:
    """Create and validate a starter, binding its project for the scope.

    Creation never searches parent directories or overwrites an existing file.
    A created file remains on disk if subsequent validation fails.
    """
    filename = settings.static_config.get().config_filename
    if filename is None:
        raise errors.ConfigFilenameNotSet()
    selected = initialize_config(filename, package=package, template=template, cwd=cwd, path=path)
    with _load_project_config(selected, config_class) as result:
        yield result


@contextmanager
def _load_project_config[T: pydantic.BaseModel](
    selected: Result[ProjectConfigPath], config_class: type[T]
) -> Iterator[Result[T]]:
    if selected.is_err():
        yield Err(selected.unwrap_err())
        return
    path = selected.unwrap()
    loaded = load_config(path, config_class)
    if loaded.is_err():
        yield loaded
        return
    with project_config.scope(ProjectConfig(config_path=path)):
        yield loaded
