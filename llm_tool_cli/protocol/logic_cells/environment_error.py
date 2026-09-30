from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.protocol.logic_cells.uniform import UniformCell
from llm_tool_cli.protocol.output_cells.base import OutputCell, to_meta_value


class EnvironmentErrorCell(UniformCell):
    """An operational failure retained as typed data until projection."""

    error: EnvironmentError

    def _render(self, cell_type: type[OutputCell]) -> OutputCell:
        record = self.error.as_record()
        content = str(record.pop("message"))
        fixes = [fix.format(error=self.error).strip() for fix in self.error.ways_to_fix]
        if len(fixes) == 1:
            content = f"{content}\nWay to fix: {fixes[0]}"
        elif fixes:
            guidance = "\n".join(f"- {fix}" for fix in fixes)
            content = f"{content}\n\nWays to fix:\n\n{guidance}"
        return cell_type(
            kind="error",
            media_type="text/markdown",
            content=content,
            meta={key: to_meta_value(value) for key, value in record.items()},
        )
