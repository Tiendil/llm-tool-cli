"""Scoped application, runtime, and project settings for consumer tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from llm_tool_cli.config.project import ProjectConfig, project_config
from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core.settings import ConfigFilename, StaticConfig, ToolLabel, static_config
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol


@pytest.fixture
def project_static_settings() -> Iterator[StaticConfig]:
    value = StaticConfig(tool_label=ToolLabel("TEST"), config_filename=ConfigFilename("tool.toml"))
    with static_config.scope(value):
        yield value


@pytest.fixture
def runtime_settings() -> Iterator[RuntimeConfig]:
    value = RuntimeConfig(protocol=Protocol.human)
    with runtime_config.scope(value):
        yield value


@pytest.fixture
def project_settings(tmp_path: Path) -> Iterator[ProjectConfig]:
    """Bind a project rooted at the test directory without filesystem loading."""
    value = ProjectConfig(config_path=ProjectConfigPath(tmp_path / "config.toml"))
    with project_config.scope(value):
        yield value
