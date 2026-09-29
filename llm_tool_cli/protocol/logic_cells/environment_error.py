from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.output_cells import AutomationOutputCell, HumanOutputCell, LLMOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell, to_meta_value


class EnvironmentErrorCell(LogicCell):
    """An operational failure retained as typed data until projection."""

    error: EnvironmentError

    def render_human(self) -> list[OutputCell]:
        return self._render(HumanOutputCell)

    def render_llm(self) -> list[OutputCell]:
        return self._render(LLMOutputCell)

    def render_automation(self) -> list[OutputCell]:
        return self._render(AutomationOutputCell)

    def _render(self, cell_type: type[OutputCell]) -> list[OutputCell]:
        record = self.error.as_record()
        content = str(record.pop("message"))
        fixes = [fix.format(error=self.error).strip() for fix in self.error.ways_to_fix]
        if len(fixes) == 1:
            content = f"{content}\nWay to fix: {fixes[0]}"
        elif fixes:
            guidance = "\n".join(f"- {fix}" for fix in fixes)
            content = f"{content}\n\nWays to fix:\n\n{guidance}"
        return [
            cell_type(
                kind="error",
                media_type="text/markdown",
                content=content,
                meta={key: to_meta_value(value) for key, value in record.items()},
            )
        ]
