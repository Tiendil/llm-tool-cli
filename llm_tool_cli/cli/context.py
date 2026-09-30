from collections.abc import Iterable

import typer

from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.rendering import write_cells

_GLOBAL_OPTIONS_CONTEXT_KEY = "llm_tool_cli.global_options"


def set_global_options(context: typer.Context, options: GlobalOptions) -> None:
    context.find_root().meta[_GLOBAL_OPTIONS_CONTEXT_KEY] = options


def get_global_options(context: typer.Context) -> GlobalOptions:
    options = context.find_root().meta.get(_GLOBAL_OPTIONS_CONTEXT_KEY)
    if isinstance(options, GlobalOptions):
        return options
    return GlobalOptions()


class CommandContext:
    __slots__ = ("global_options", "protocol")

    def __init__(self, context: typer.Context) -> None:
        self.global_options = get_global_options(context)
        self.protocol = self.global_options.protocol_for(context.info_name or "")

    def write_cells(self, cells: Iterable[LogicCell], *, stderr: bool = False) -> None:
        write_cells(cells, protocol=self.protocol, stderr=stderr)
