import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.core import settings


@pytest.fixture
def isolated_settings(mocker: MockerFixture) -> None:
    """Start with an unset label and restore the previous state after the test."""
    # Approved test-only reset: production initialization cannot unset or replace
    # a label. Keep real initialization and access; pytest-mock restores the state.
    mocker.patch.object(settings, "_tool_label", None)
