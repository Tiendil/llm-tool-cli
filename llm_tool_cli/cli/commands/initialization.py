from pathlib import Path

import pydantic
import typer

from llm_tool_cli.cli.context import command_context
from llm_tool_cli.config import initialize_project
from llm_tool_cli.config.project import project_config
from llm_tool_cli.output import output
from llm_tool_cli.paths import PathInput
from llm_tool_cli.protocol.cell_shortcuts import configuration_created


def register_init_command(
    app: typer.Typer,
    *,
    config_class: type[pydantic.BaseModel],
    package: str,
    template: str,
    help: str | None = None,
) -> None:
    """Register project initialization using the supplied schema and starter."""

    @app.command("init", help=help)
    def init(context: typer.Context) -> None:
        with command_context(context) as command:
            context.with_resource(
                initialize_project(
                    config_class,
                    package=package,
                    template=template,
                    cwd=PathInput(Path.cwd()),
                    path=command.config_input,
                )
            ).unwrap()
            output.get().emit([configuration_created(project_config.get().config_path)]).unwrap()
