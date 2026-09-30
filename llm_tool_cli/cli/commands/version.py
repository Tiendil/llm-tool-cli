from importlib import metadata

import typer

from llm_tool_cli.cli.context import get_global_options
from llm_tool_cli.cli.entities import ExitCode
from llm_tool_cli.protocol import cell_shortcuts
from llm_tool_cli.protocol.rendering import write_cells


def register_version_command(app: typer.Typer, *, distribution: str) -> None:
    """Register version output for the supplied installed distribution."""

    @app.command("version", help="Print the installed package version.")
    def version(context: typer.Context) -> None:
        protocol = get_global_options(context).protocol_for("version")
        value = metadata.version(distribution)
        write_cells([cell_shortcuts.version(value)], protocol=protocol)
        raise typer.Exit(ExitCode.success)
