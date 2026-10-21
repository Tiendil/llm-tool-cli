import uuid

import pydantic
import pytest

from llm_tool_cli.protocol.errors import ContentWithoutMediaType
from llm_tool_cli.protocol.output_cells import HumanOutputCell
from llm_tool_cli.protocol.output_cells.base import MetaValue, RenderContext, to_meta_value


class TestToMetaValue:
    @pytest.mark.parametrize(
        ("value", "expected"),
        (
            ("value", "value"),
            ("  Заметка  ", "  Заметка  "),
            (1, 1),
            (True, True),
            (None, None),
            ([], []),
            (["first", " second "], ["first", " second "]),
            (["first", 2], "['first', 2]"),
            ({"count": 2}, "{'count': 2}"),
            (1.5, "1.5"),
            (uuid.UUID("12345678-1234-5678-9234-567812345678"), "12345678-1234-5678-9234-567812345678"),
        ),
    )
    def test_converts_metadata_values(self, value: object, expected: MetaValue) -> None:
        assert to_meta_value(value) == expected


class TestOutputCell:
    @pytest.mark.parametrize("content", ("content", ""))
    def test_build__requires_media_type_when_content_is_present(self, content: str) -> None:
        with pytest.raises(ContentWithoutMediaType):
            HumanOutputCell.build(kind="status", media_type=None, content=content)

    def test_build__stores_metadata_as_cell_metadata(self) -> None:
        cell = HumanOutputCell.build(kind="status", media_type="text/plain", content="content", count=2, label="ready")

        assert cell.meta == {"count": 2, "label": "ready"}

    def test_build__accepts_media_type_without_content(self) -> None:
        cell = HumanOutputCell.build(kind="status", media_type="text/plain", content=None)

        assert cell.media_type == "text/plain"
        assert cell.content is None

    def test_build_meta__generates_fresh_uuid4_identifiers(self) -> None:
        first = HumanOutputCell.build_meta(kind="status")
        second = HumanOutputCell.build_meta(kind="status")

        assert first.id.version == 4
        assert second.id.version == 4
        assert first.id != second.id

    def test_build_meta__creates_contentless_cell(self) -> None:
        cell = HumanOutputCell.build_meta(kind="status", count=0)

        assert cell.media_type is None
        assert cell.content is None
        assert cell.meta == {"count": 0}

    def test_build_markdown__uses_markdown_media_type(self) -> None:
        cell = HumanOutputCell.build_markdown(kind="status", content="# Done", count=1)

        assert cell.media_type == "text/markdown"
        assert cell.meta == {"count": 1}

    def test_short_id__returns_unpadded_urlsafe_base64_id(self) -> None:
        cell = HumanOutputCell.build_meta(kind="status").replace(id=uuid.UUID("12345678-1234-5678-9234-567812345678"))

        assert cell.short_id == "EjRWeBI0VniSNFZ4EjRWeA"


class TestRenderContext:
    @pytest.mark.parametrize(("index", "total"), [(-1, 1), (0, 0), (1, 1), (3, 2)])
    def test_validate_position__rejects_invalid_sequence_position(self, index: int, total: int) -> None:
        with pytest.raises(pydantic.ValidationError):
            RenderContext(index=index, total=total, tool_label="TOOL")

    @pytest.mark.parametrize(("index", "total"), [(0, 1), (0, 2), (1, 2)])
    def test_validate_position__accepts_sequence_boundaries(self, index: int, total: int) -> None:
        context = RenderContext(index=index, total=total, tool_label="TOOL")

        assert (context.index, context.total) == (index, total)
