import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.core import settings
from llm_tool_cli.core.context import ContextValue


@pytest.fixture
def isolated_settings(mocker: MockerFixture) -> None:
    """Start with unset static settings and restore the previous state after the test."""
    # Approved test-only reset: replace the binding because production initialization
    # cannot clear it. Keep real initialization and access; pytest-mock restores it.
    mocker.patch.object(settings, "static_config", ContextValue[settings.StaticConfig]("static_config"))
