from pathlib import Path
from typing import Annotated

import typer

from llm_tool_cli.cli.entities import ExitCode
from llm_tool_cli.cli.errors import InvalidProtocol
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import environment_error
from llm_tool_cli.protocol.rendering import write_cells


def _parse_config_path(value: str) -> ProjectConfigPath:
    return ProjectConfigPath(Path(value))


ConfigOption = Annotated[
    ProjectConfigPath | None,
    typer.Option(
        "--config",
        parser=_parse_config_path,
        metavar="PATH",
        help="Configuration file path. Overrides the command's default configuration location.",
    ),
]


def _parse_protocol(value: str) -> Protocol:
    try:
        return Protocol(value)
    except ValueError as error:
        choices = ", ".join(protocol.value for protocol in Protocol)
        failure = InvalidProtocol(reason=f"invalid protocol `{value}`; expected one of: {choices}")
        write_cells([environment_error(failure)], protocol=Protocol.llm, stderr=True)
        raise typer.Exit(ExitCode.invalid_arguments) from error


ProtocolOption = Annotated[
    Protocol | None,
    typer.Option(
        "--protocol",
        "-p",
        parser=_parse_protocol,
        metavar="PROTOCOL",
        help=(
            f"Output protocol ({', '.join(protocol.value for protocol in Protocol)}). "
            "Defaults to llm for skill and human for other commands."
        ),
    ),
]
