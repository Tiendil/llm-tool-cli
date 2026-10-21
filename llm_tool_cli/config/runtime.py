"""Effective runtime settings, independent of their input source."""

from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.protocol import Protocol


class RuntimeConfig(BaseEntity):
    """Complete settings for an execution, including commands without a project."""

    protocol: Protocol


runtime_config = ContextValue[RuntimeConfig]("runtime_config")
