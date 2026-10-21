import json

import pytest

from llm_tool_cli.protocol.output_cells.automation import AutomationOutputCell
from llm_tool_cli.protocol.output_cells.base import RenderContext
from llm_tool_cli.protocol.output_cells.tests.make import cell


class TestAutomationOutputCell:
    def test_render__serializes_cell_as_sorted_json_line(self) -> None:
        formatted = cell(
            AutomationOutputCell,
        ).render(RenderContext(index=0, total=1, tool_label="TOOL"))

        assert json.loads(formatted) == {
            "alpha": "first",
            "content": "Sample content.",
            "enabled": True,
            "id": "EjRWeBI0VniSNFZ4EjRWeA",
            "missing": None,
            "zeta": 2,
        }
        assert formatted == (
            b'{"alpha":"first","content":"Sample content.","enabled":true,'
            b'"id":"EjRWeBI0VniSNFZ4EjRWeA","missing":null,"zeta":2}\n'
        )

    @pytest.mark.parametrize("content", [None, ""])
    def test_render__serializes_missing_content_as_null(self, content: str | None) -> None:
        formatted = cell(AutomationOutputCell, content=content).render(
            RenderContext(index=0, total=1, tool_label="TOOL")
        )

        assert json.loads(formatted)["content"] is None

    def test_render__preserves_metadata_field_precedence(self) -> None:
        source = cell(AutomationOutputCell, content="Actual content", meta={"id": "metadata-id", "content": "ignored"})

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL"))

        assert json.loads(formatted) == {"id": "metadata-id", "content": "Actual content"}

    def test_render__preserves_unicode_and_list_metadata(self) -> None:
        source = cell(
            AutomationOutputCell, content="日本語\nSecond line.", meta={"labels": ["一", "two"], "enabled": False}
        )

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL"))

        assert json.loads(formatted) == {
            "id": source.short_id,
            "content": "日本語\nSecond line.",
            "labels": ["一", "two"],
            "enabled": False,
        }
        assert "日本語".encode() in formatted
        assert len(formatted.splitlines()) == 1
