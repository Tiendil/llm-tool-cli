from importlib import metadata

import typer

from llm_tool_cli.cli.context import CommandContext
from llm_tool_cli.cli.handling import handle_command_errors
from llm_tool_cli.protocol import cell_shortcuts


def register_version_command(app: typer.Typer, *, distribution: str) -> None:
    """Register version output for the supplied installed distribution."""

    @app.command("version", help="Print the installed package version.")
    def version(context: typer.Context) -> None:
        command = CommandContext(context)
        with handle_command_errors(protocol=command.protocol):
            value = metadata.version(distribution)
            command.write_cells([cell_shortcuts.version(value)])
