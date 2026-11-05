from collections.abc import Callable

import typer

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.commands.cache import register_cache_clean_command
from llm_tool_cli.core.result import Result
from llm_tool_cli.tool_cache import ToolCache


def cache_app(
    factory: Callable[[typer.Context], Result[ToolCache]], *, group_name: str | None = "objects"
) -> typer.Typer:
    app = create_app(help="Manage cached objects.")
    target = app
    if group_name is not None:
        target = typer.Typer(no_args_is_help=True, context_settings={"help_option_names": ["-h", "--help"]})
        app.add_typer(target, name=group_name)
    register_cache_clean_command(target, cache_factory=factory)
    return app
