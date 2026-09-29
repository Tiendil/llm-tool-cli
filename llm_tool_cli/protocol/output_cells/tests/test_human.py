from llm_tool_cli.protocol.output_cells.base import RenderContext
from llm_tool_cli.protocol.output_cells.human import HumanOutputCell
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

        assert formatted == (
            "----- TOOL CELL EjRWeBI0VniSNFZ4EjRWeA -----\n"
            "kind = sample_status\n"
            "media_type = text/markdown\n"
            "alpha = first\n"
            "enabled = True\n"
            "missing = None\n"
            "zeta = 2\n"
            "\n"
            "Sample content.\n"
            "\n"
        )

    def test_render__omits_media_type_and_content_when_absent(self) -> None:
        formatted = (
            cell(HumanOutputCell, media_type=None, content=None, meta={})
            .render(RenderContext(index=0, total=1, tool_label="TOOL"))
            .decode()
        )

        assert formatted == "----- TOOL CELL EjRWeBI0VniSNFZ4EjRWeA -----\nkind = sample_status\n\n"

    def test_render__omits_empty_content_section(self) -> None:
        formatted = (
            cell(HumanOutputCell, content="", meta={})
            .render(RenderContext(index=0, total=1, tool_label="TOOL"))
            .decode()
        )

        assert formatted == (
            "----- TOOL CELL EjRWeBI0VniSNFZ4EjRWeA -----\n" "kind = sample_status\nmedia_type = text/markdown\n\n"
        )

    def test_render__preserves_unicode_content_and_list_metadata(self) -> None:
        source = cell(HumanOutputCell, content="日本語\nSecond line.", meta={"labels": ["一", "two"]})

        formatted = source.render(RenderContext(index=0, total=1, tool_label="TOOL")).decode()

        assert formatted == (
            "----- TOOL CELL EjRWeBI0VniSNFZ4EjRWeA -----\n"
            "kind = sample_status\nmedia_type = text/markdown\n"
            "labels = ['一', 'two']\n\n日本語\nSecond line.\n\n"
        )
