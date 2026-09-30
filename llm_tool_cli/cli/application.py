import typer

from llm_tool_cli.cli.context import set_global_options
from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.cli.options import ConfigOption, ProtocolOption


def create_app(*, help: str) -> typer.Typer:
    app = typer.Typer(
        help=help,
        add_completion=True,
        context_settings={"help_option_names": ["-h", "--help"]},
    )

    @app.callback()
    def initialize(
        context: typer.Context,
        protocol: ProtocolOption = None,
        config_path: ConfigOption = None,
    ) -> None:
        set_global_options(context, GlobalOptions(protocol=protocol, config_path=config_path))

    return app
