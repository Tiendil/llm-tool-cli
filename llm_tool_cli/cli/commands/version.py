from importlib import metadata

import typer

from llm_tool_cli.cli.context import command_context
from llm_tool_cli.output import output
from llm_tool_cli.protocol import cell_shortcuts


def register_version_command(app: typer.Typer, *, distribution: str) -> None:
    """Register version output for the supplied installed distribution."""

    @app.command("version", help="Print the installed package version.")
    def version(context: typer.Context) -> None:
        with command_context(context):
            value = metadata.version(distribution)
            output.get().emit([cell_shortcuts.version(value)]).unwrap()
