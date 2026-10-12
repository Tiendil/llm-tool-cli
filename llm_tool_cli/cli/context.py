from collections.abc import Iterable

import typer

from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.rendering import write_cells

global_options = ContextValue[GlobalOptions]("global_options")


class CommandContext:
    __slots__ = ("global_options", "protocol")

    def __init__(self, context: typer.Context) -> None:
        self.global_options = global_options.get() if global_options.is_set() else GlobalOptions()
        self.protocol = self.global_options.protocol_for(context.info_name or "")

    def write_cells(self, cells: Iterable[LogicCell], *, stderr: bool = False) -> None:
        write_cells(cells, protocol=self.protocol, stderr=stderr)
