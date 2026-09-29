import pytest

from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.errors import ContentWithoutMediaType
from llm_tool_cli.protocol.logic_cells import ContentCell
from llm_tool_cli.protocol.output_cells import AutomationOutputCell, HumanOutputCell, LLMOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell


class TestContentCell:
    @pytest.mark.parametrize(
        ("protocol", "cell_type"),
        [
            (Protocol.human, HumanOutputCell),
            (Protocol.llm, LLMOutputCell),
            (Protocol.automation, AutomationOutputCell),
        ],
    )
    @pytest.mark.parametrize(("media_type", "content"), [("text/markdown", "café"), (None, None), ("text/plain", "")])
    def test_render__preserves_payload_and_creates_fresh_output(
        self, protocol: Protocol, cell_type: type[OutputCell], media_type: str | None, content: str | None
    ) -> None:
        cell = ContentCell(
            kind="item",
            media_type=media_type,
            content=content,
            meta={"labels": ["one", "two"], "enabled": True, "empty": None},
        )
        original = cell.model_dump()

        first = cell.render(protocol)
        second = cell.render(protocol)

        assert len(first) == len(second) == 1
        assert isinstance(first[0], cell_type)
        assert isinstance(second[0], cell_type)
        assert first[0].model_dump(exclude={"id"}) == second[0].model_dump(exclude={"id"}) == original
        assert first[0].id.version == second[0].id.version == 4
        assert first[0].id != second[0].id
        assert cell.model_dump() == original

    @pytest.mark.parametrize("content", ["text", ""])
    def test_validate_content__rejects_missing_media_type(self, content: str) -> None:
        with pytest.raises(ContentWithoutMediaType):
            ContentCell(kind="item", content=content)

    def test_render__preserves_reserved_metadata_fields(self) -> None:
        cell = ContentCell(kind="item", meta={"id": "custom", "content": "metadata", "kind": "metadata_kind"})

        output = cell.render(Protocol.automation)[0]

        assert output.kind == "item"
        assert output.content is None
        assert output.meta == cell.meta
