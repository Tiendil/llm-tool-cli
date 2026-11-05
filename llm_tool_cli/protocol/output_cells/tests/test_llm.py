import pytest

from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.protocol.output_cells.base import RenderContext
from llm_tool_cli.protocol.output_cells.llm import LLMOutputCell
from llm_tool_cli.protocol.output_cells.tests.make import cell


class TestLLMOutputCell:
    @pytest.mark.parametrize(("name", "label"), [("demo-tool", "DEMO-TOOL"), (" tool-2 ", "TOOL-2")])
    def test_render__derives_uppercase_label_from_name(self, name: str, label: str) -> None:
        context = RenderContext(index=0, total=1, tool_name=ToolName(name))
        formatted = cell(LLMOutputCell, media_type=None, content=None, meta={}).render(context).decode()
        assert formatted == (
            f"--{label}-CELL EjRWeBI0VniSNFZ4EjRWeA BEGIN--\n"
            "kind=sample_status\n"
            f"--{label}-CELL EjRWeBI0VniSNFZ4EjRWeA END--\n"
        )
        assert context.tool_name == name.strip()

    def test_render__renders_llm_cell_with_sorted_metadata(self) -> None:
        formatted = (
            cell(
                LLMOutputCell,
            )
            .render(RenderContext(index=0, total=1, tool_name=ToolName("tool")))
            .decode()
        )

        assert formatted == (
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA BEGIN--\n"
            "kind=sample_status\n"
            "media_type=text/markdown\n"
            "alpha=first\n"
            "enabled=True\n"
            "missing=None\n"
            "zeta=2\n"
            "\n"
            "Sample content.\n"
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA END--\n"
        )

    def test_render__omits_media_type_and_content_when_absent(self) -> None:
        formatted = (
            cell(LLMOutputCell, media_type=None, content=None, meta={})
            .render(RenderContext(index=0, total=1, tool_name=ToolName("tool")))
            .decode()
        )

        assert formatted == (
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA BEGIN--\n"
            "kind=sample_status\n"
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA END--\n"
        )

    def test_render__omits_empty_content_section(self) -> None:
        formatted = (
            cell(LLMOutputCell, content="", meta={})
            .render(RenderContext(index=0, total=1, tool_name=ToolName("tool")))
            .decode()
        )

        assert formatted == (
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA BEGIN--\n"
            "kind=sample_status\nmedia_type=text/markdown\n"
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA END--\n"
        )

    def test_render__preserves_unicode_content_and_list_metadata(self) -> None:
        source = cell(LLMOutputCell, content="日本語\nSecond line.", meta={"labels": ["一", "two"]})

        formatted = source.render(RenderContext(index=0, total=1, tool_name=ToolName("tool"))).decode()

        assert formatted == (
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA BEGIN--\n"
            "kind=sample_status\nmedia_type=text/markdown\n"
            "labels=['一', 'two']\n\n日本語\nSecond line.\n"
            "--TOOL-CELL EjRWeBI0VniSNFZ4EjRWeA END--\n"
        )
