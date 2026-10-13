from collections.abc import Iterable

import typer

from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.output import StreamOutputEmitter, output
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells.base import LogicCell


class CommandContext:
    __slots__ = ("_context",)

    def __init__(self, context: typer.Context) -> None:
        self._context = context
        protocol = context.find_root().params.get("protocol")
        if protocol is None:
            protocol = Protocol.llm if context.info_name == "skill" else Protocol.human
        context.with_resource(runtime_config.scope(RuntimeConfig(protocol=protocol)))
        context.with_resource(output.scope(StreamOutputEmitter()))

    @property
    def config_input(self) -> ProjectConfigPath | None:
        """Unresolved CLI input for configuration loading or creation."""
        return self._context.find_root().params.get("config_path")

    @property
    def protocol(self) -> Protocol:
        return runtime_config.get().protocol

    def write_cells(self, cells: Iterable[LogicCell]) -> None:
        output.get().emit(list(cells)).unwrap()
