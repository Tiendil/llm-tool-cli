import typer

from llm_tool_cli.cli.entities import GlobalOptions

_GLOBAL_OPTIONS_CONTEXT_KEY = "llm_tool_cli.global_options"


def set_global_options(context: typer.Context, options: GlobalOptions) -> None:
    context.find_root().meta[_GLOBAL_OPTIONS_CONTEXT_KEY] = options


def get_global_options(context: typer.Context) -> GlobalOptions:
    options = context.find_root().meta.get(_GLOBAL_OPTIONS_CONTEXT_KEY)
    if isinstance(options, GlobalOptions):
        return options
    return GlobalOptions()
