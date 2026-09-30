import pytest

from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells.uniform import UniformCell
from llm_tool_cli.protocol.output_cells import AutomationOutputCell, HumanOutputCell, LLMOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell


class ExampleUniformCell(UniformCell):
    items: tuple[str, ...]

    def _render(self, cell_type: type[OutputCell]) -> OutputCell:
        return cell_type.build_markdown(kind="items", content="\n".join(self.items), items=list(self.items))


class TestUniformCell:
    @pytest.mark.parametrize(
        ("protocol", "cell_type"),
        [
            (Protocol.human, HumanOutputCell),
            (Protocol.llm, LLMOutputCell),
            (Protocol.automation, AutomationOutputCell),
        ],
    )
    @pytest.mark.parametrize("items", [(), ("first", "café")])
    def test_render__projects_one_fresh_cell_without_mutating_input(
        self, protocol: Protocol, cell_type: type[OutputCell], items: tuple[str, ...]
    ) -> None:
        cell = ExampleUniformCell(items=items)
        original = cell.model_dump()

        first = cell.render(protocol)
        second = cell.render(protocol)

        assert len(first) == len(second) == 1
        assert isinstance(first[0], cell_type)
        assert isinstance(second[0], cell_type)
        assert (
            first[0].model_dump(exclude={"id"})
            == second[0].model_dump(exclude={"id"})
            == {
                "kind": "items",
                "media_type": "text/markdown",
                "content": "\n".join(items),
                "meta": {"items": list(items)},
            }
        )
        assert first[0].id != second[0].id
        assert cell.model_dump() == original
