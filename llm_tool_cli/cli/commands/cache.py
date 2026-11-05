from collections.abc import Callable

import typer

from llm_tool_cli.cli.context import command_context
from llm_tool_cli.core.result import Result
from llm_tool_cli.output import output
from llm_tool_cli.tool_cache import ToolCache
from llm_tool_cli.tool_cache.cells import CacheCleanCell


def register_cache_clean_command(
    app: typer.Typer,
    *,
    cache_factory: Callable[[typer.Context], Result[ToolCache]],
    help: str = "Clear owned cached data without changing projects or original sources.",
) -> None:
    """Register only ``clean`` on the supplied app; the caller owns any group.

    The factory runs inside the command scope and may retain invocation
    resources through the supplied context. It owns cache selection and policy.
    Registration, help, and parsing never construct or access the cache.
    """

    @app.command("clean", help=help)
    def clean(context: typer.Context) -> None:
        with command_context(context):
            cache = cache_factory(context).unwrap()
            changed = cache.clean().unwrap()
            output.get().emit([CacheCleanCell(cache_dir=cache.root, changed=changed)]).unwrap()
