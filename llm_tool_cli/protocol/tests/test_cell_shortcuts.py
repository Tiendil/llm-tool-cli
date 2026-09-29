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


class TestSkill:
    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("content", ["# Custom guide\n\nInstructions for café.", ""])
    def test_shared_skill_payload(self, protocol: Protocol, content: str) -> None:
        cell = cell_shortcuts.skill(document="custom-guide", content=content)

        outputs = cell.render(protocol)

        assert len(outputs) == 1
        assert outputs[0].model_dump(exclude={"id"}) == {
            "kind": "skill",
            "media_type": "text/markdown",
            "content": content,
            "meta": {"type": "skill", "document": "custom-guide"},
        }

    def test_empty_document_name(self) -> None:
        cell = cell_shortcuts.skill(document="", content="Instructions.")

        assert cell.meta == {"type": "skill", "document": ""}


class TestEnvironmentError:
    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_retains_error_until_projection(self, protocol: Protocol) -> None:
        error = EnvironmentError(code="unavailable", message="Try later.", ways_to_fix=["Retry."])

        cell = cell_shortcuts.environment_error(error)

        assert isinstance(cell, EnvironmentErrorCell)
        assert cell.error == error
        assert cell.render(protocol)[0].content == "Try later.\nWay to fix: Retry."
