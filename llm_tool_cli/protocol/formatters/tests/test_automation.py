import json

import pytest

from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.protocol.formatters.automation import Formatter
from llm_tool_cli.protocol.formatters.tests.make import cell


class TestFormatter:
    def test_format_error__preserves_shared_record_without_cell_fields(self) -> None:
        error = EnvironmentError(message="unavailable", code="unavailable")

        formatted = Formatter().format_error(error)

        assert json.loads(formatted) == error.as_record()
        assert formatted.endswith(b"\n")
        assert len(formatted.splitlines()) == 1

    def test_format_cell__serializes_cell_as_sorted_json_line(self) -> None:
        formatted = Formatter().format_cell(cell())

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
    def test_format_cell__serializes_missing_content_as_null(self, content: str | None) -> None:
        formatted = Formatter().format_cell(cell(content=content))

        assert json.loads(formatted)["content"] is None

    def test_format_cell__preserves_metadata_field_precedence(self) -> None:
        source = cell(content="Actual content", meta={"id": "metadata-id", "content": "ignored"})

        formatted = Formatter().format_cell(source)

        assert json.loads(formatted) == {"id": "metadata-id", "content": "Actual content"}

    def test_format_cell__preserves_unicode_and_list_metadata(self) -> None:
        source = cell(content="日本語\nSecond line.", meta={"labels": ["一", "two"], "enabled": False})

        formatted = Formatter().format_cell(source)

        assert json.loads(formatted) == {
            "id": source.short_id,
            "content": "日本語\nSecond line.",
            "labels": ["一", "two"],
            "enabled": False,
        }
        assert "日本語".encode() in formatted
        assert len(formatted.splitlines()) == 1
