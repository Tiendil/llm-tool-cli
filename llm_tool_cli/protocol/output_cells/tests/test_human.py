import pytest

from llm_tool_cli.protocol.output_cells.base import RenderContext
from llm_tool_cli.protocol.output_cells.human import HumanErrorOutputCell, HumanOutputCell, HumanWarningOutputCell
from llm_tool_cli.protocol.output_cells.tests.make import cell


class TestHumanOutputCell:
    def test_render__renders_human_cell_with_sorted_metadata(self) -> None:
        formatted = (
            cell(
                HumanOutputCell,
            )
            .render(RenderContext(index=0, total=1, tool_label="TOOL"))
            .decode()
        )

        assert formatted == "alpha: first\nenabled: True\nmissing: None\nzeta: 2\n\nSample content.\n\n"

    def test_render__omits_media_type_and_content_when_absent(self) -> None:
        formatted = (
            cell(HumanOutputCell, media_type=None, content=None, meta={})
            .render(RenderContext(index=0, total=1, tool_label="TOOL"))
            .decode()
        )

        assert formatted == "sample_status\n\n"

    def test_render__omits_empty_content_section(self) -> None:
        formatted = (
            cell(HumanOutputCell, content="", meta={})
            .render(RenderContext(index=0, total=1, tool_label="TOOL"))
            .decode()
        )

        assert formatted == "sample_status\n\n"

    def test_render__preserves_unicode_content_and_list_metadata(self) -> None:
        source = cell(HumanOutputCell, content="日本語\nSecond line.", meta={"labels": ["一", "two"]})

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == "labels: ['一', 'two']\n\n日本語\nSecond line.\n\n"

    def test_render__omits_redundant_type_and_preserves_application_metadata(self) -> None:
        source = HumanOutputCell.build_meta(kind="status", type="status", id="domain-id", count=0, labels=[])
        original = source.model_dump()

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == "count: 0\nid: domain-id\nlabels: []\n\n"
        assert source.model_dump() == original

    def test_render__preserves_type_when_it_has_a_distinct_meaning(self) -> None:
        source = HumanOutputCell.build_meta(kind="status", type="custom")

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == "type: custom\n\n"

    def test_render__shows_content_without_metadata(self) -> None:
        source = HumanOutputCell.build_markdown(kind="document", content="First paragraph.\n\nSecond paragraph.")

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == "First paragraph.\n\nSecond paragraph.\n\n"


class TestHumanErrorOutputCell:
    def test_render__shows_message_without_diagnostic_context(self) -> None:
        source = HumanErrorOutputCell.build_markdown(kind="error", content="失敗", type="error")

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == "Error: 失敗\n\n"

    def test_render__shows_message_and_guidance_before_diagnostic_context(self) -> None:
        source = HumanErrorOutputCell.build_markdown(
            kind="error",
            content="Service unavailable.\nWay to fix: Retry later.",
            type="error",
            code="unavailable",
            path="/project",
        )
        original = source.model_dump()

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == (
            "Error: Service unavailable.\nWay to fix: Retry later.\n\ncode: unavailable\npath: /project\n\n"
        )
        assert source.model_dump() == original

    @pytest.mark.parametrize("content", [None, ""])
    def test_render__retains_diagnostics_without_a_message(self, content: str | None) -> None:
        source = HumanErrorOutputCell.build(kind="error", media_type="text/markdown", content=content, code="empty")

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == "Error:\n\ncode: empty\n\n"


class TestHumanWarningOutputCell:
    @pytest.mark.parametrize("message", ["first\nsecond", "café", ""])
    def test_render__shows_warning_message_without_record_fields(self, message: str) -> None:
        source = HumanWarningOutputCell.build_meta(kind="warning", type="warning", message=message)
        original = source.model_dump()

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == f"Warning: {message}".rstrip() + "\n\n"
        assert source.model_dump() == original
