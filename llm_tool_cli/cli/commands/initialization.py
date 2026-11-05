from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pydantic
import typer

from llm_tool_cli.cli.context import command_context
from llm_tool_cli.config import initialize_project
from llm_tool_cli.config.project import project_config
from llm_tool_cli.core.result import Result
from llm_tool_cli.output import output
from llm_tool_cli.paths import PathInput, ProjectConfigPath
from llm_tool_cli.protocol.cell_shortcuts import configuration_created

type InitOperationScope = Callable[
    [PathInput, ProjectConfigPath | None], AbstractContextManager[Result[ProjectConfigPath]]
]


def register_init_command(
    app: typer.Typer,
    *,
    config_class: type[pydantic.BaseModel],
    package: str,
    template: str,
    help: str | None = None,
    operation_scope: InitOperationScope | None = None,
) -> None:
    """Register initialization with an optional consumer resource scope.

    The scope receives the invocation cwd and unresolved configuration input,
    and yields the selected configuration path or an expected failure. It is
    entered before initialization and retained through output delivery, with
    cleanup on success or failure. Registration and help never enter it.
    """

    @app.command("init", help=help)
    def init(context: typer.Context) -> None:
        with command_context(context) as command:
            cwd = PathInput(Path.cwd())
            path = command.config_input
            if operation_scope is not None:
                path = context.with_resource(operation_scope(cwd, path)).unwrap()
            context.with_resource(
                initialize_project(
                    config_class,
                    package=package,
                    template=template,
                    cwd=cwd,
                    path=path,
                )
            ).unwrap()
            output.get().emit([configuration_created(project_config.get().config_path)]).unwrap()
