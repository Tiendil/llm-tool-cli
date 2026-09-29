import pytest

from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.protocol import Protocol, cell_shortcuts
from llm_tool_cli.protocol.logic_cells import EnvironmentErrorCell


class TestOperationSucceeded:
    def test_creates_markdown_operation_succeeded_cell(self) -> None:
        cell = cell_shortcuts.operation_succeeded("Done.", operation="setup")

        assert cell.kind == "operation_succeeded"
        assert cell.media_type == "text/markdown"
        assert cell.content == "Done."
        assert cell.meta == {"operation": "setup"}


class TestOperationFailed:
    def test_creates_markdown_operation_failed_cell(self) -> None:
        cell = cell_shortcuts.operation_failed("Failed.", operation="setup")

        assert cell.kind == "operation_failed"
        assert cell.media_type == "text/markdown"
        assert cell.content == "Failed."
        assert cell.meta == {"operation": "setup"}


class TestInfo:
    def test_creates_markdown_info_cell(self) -> None:
        cell = cell_shortcuts.info("Ready.", scope="workspace")

        assert cell.kind == "info"
        assert cell.media_type == "text/markdown"
        assert cell.content == "Ready."
        assert cell.meta == {"scope": "workspace"}


class TestEnvironmentError:
    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_retains_error_until_projection(self, protocol: Protocol) -> None:
        error = EnvironmentError(code="unavailable", message="Try later.", ways_to_fix=["Retry."])

        cell = cell_shortcuts.environment_error(error)

        assert isinstance(cell, EnvironmentErrorCell)
        assert cell.error == error
        assert cell.render(protocol)[0].content == "Try later.\nWay to fix: Retry."
