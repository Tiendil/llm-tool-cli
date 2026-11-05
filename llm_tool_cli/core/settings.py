"""Application settings bound before command-line parsing in the active context."""

from typing import NewType

import pydantic

from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.core.entities import BaseEntity, ToolName
from llm_tool_cli.core.errors import ContextValueAlreadySet

ConfigFilename = NewType("ConfigFilename", str)


class StaticConfig(BaseEntity):
    """Application identity available before command-line parsing."""

    model_config = pydantic.ConfigDict(str_strip_whitespace=False)

    tool_name: ToolName
    config_filename: ConfigFilename | None = None


static_config = ContextValue[StaticConfig]("static_config")


def initialize(*, name: ToolName, config_filename: ConfigFilename | None = None) -> None:
    value = StaticConfig(tool_name=name, config_filename=config_filename)
    if static_config.is_set():
        current = static_config.get()

        if current != value:
            raise ContextValueAlreadySet(details={"name": "static_config"})
        return

    static_config.initialize(value)
