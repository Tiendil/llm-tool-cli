from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import typer

from llm_tool_cli.cli.handling import handle_command_errors, report_errors_and_exit
from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core import settings
from llm_tool_cli.core.result import UnwrapError
from llm_tool_cli.output import StreamOutputEmitter, output
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.tool_cache import resolve_cache_root


class CommandContext:
    __slots__ = ("_context",)

    def __init__(self, context: typer.Context) -> None:
        self._context = context
        protocol = context.find_root().params.get("protocol")
        if protocol is None:
            protocol = Protocol.llm if context.info_name == "skill" else Protocol.human
        cache_input = context.find_root().params.get("cache_dir")
        try:
            cache_dir = resolve_cache_root(
                settings.static_config.get().tool_name,
                Path(cache_input) if cache_input is not None else None,
                cwd=Path.cwd(),
            ).unwrap()
        except UnwrapError as error:
            report_errors_and_exit(error.errors, protocol=protocol)
        context.with_resource(runtime_config.scope(RuntimeConfig(protocol=protocol, cache_dir=cache_dir)))
        context.with_resource(output.scope(StreamOutputEmitter()))

    @property
    def config_input(self) -> ProjectConfigPath | None:
        """Unresolved CLI input for configuration loading or creation."""
        return self._context.find_root().params.get("config_path")

    @property
    def protocol(self) -> Protocol:
        return runtime_config.get().protocol


@contextmanager
def command_context(context: typer.Context) -> Iterator[CommandContext]:
    """Set up command execution and finalize output before framework cleanup."""
    command = CommandContext(context)
    with handle_command_errors(protocol=command.protocol):
        yield command
