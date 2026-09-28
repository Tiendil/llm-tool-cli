from llm_tool_cli.protocol.formatters.human import Formatter
from llm_tool_cli.protocol.formatters.tests.make import cell


class TestFormatter:
    def test_format_cell__renders_human_cell_with_sorted_metadata(self) -> None:
        formatted = Formatter(tool_label="TOOL").format_cell(cell()).decode()

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

    def test_format_cell__omits_media_type_and_content_when_absent(self) -> None:
        formatted = Formatter(tool_label="TOOL").format_cell(cell(media_type=None, content=None, meta={})).decode()

        assert formatted == "----- TOOL CELL EjRWeBI0VniSNFZ4EjRWeA -----\nkind = sample_status\n\n"

    def test_format_cell__omits_empty_content_section(self) -> None:
        formatted = Formatter(tool_label="TOOL").format_cell(cell(content="", meta={})).decode()

        assert formatted == (
            "----- TOOL CELL EjRWeBI0VniSNFZ4EjRWeA -----\n" "kind = sample_status\nmedia_type = text/markdown\n\n"
        )

    def test_format_cell__preserves_unicode_content_and_list_metadata(self) -> None:
        source = cell(content="日本語\nSecond line.", meta={"labels": ["一", "two"]})

        formatted = Formatter(tool_label="TOOL").format_cell(source).decode()

        assert formatted == (
            "----- TOOL CELL EjRWeBI0VniSNFZ4EjRWeA -----\n"
            "kind = sample_status\nmedia_type = text/markdown\n"
            "labels = ['一', 'two']\n\n日本語\nSecond line.\n\n"
        )
