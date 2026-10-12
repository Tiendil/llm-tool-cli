import typer

from llm_tool_cli.cli.options import ConfigOption, ProtocolOption


def create_app(*, help: str) -> typer.Typer:
    app = typer.Typer(
        help=help,
        add_completion=True,
        context_settings={"help_option_names": ["-h", "--help"]},
    )

    @app.callback()
    def initialize(
        protocol: ProtocolOption = None,
        config_path: ConfigOption = None,
    ) -> None:
        """Declare global options for command-specific runtime setup."""
        # Typer uses this callback's signature to register --protocol/-p and
        # --config on the root command group. Before calling it, the framework
        # parses these options and stores them in the root context's params;
        # this function does not need to store or forward the values itself.
        # CommandContext reads them through context.find_root().params when the
        # selected command starts. It can then choose the command's default
        # protocol and bind RuntimeConfig, while leaving configuration path
        # resolution and loading to commands that actually need a workspace.
        # The callback therefore intentionally performs no initialization.
        # Removing it would remove the global option declarations and could
        # make a single-command application lose its command-group interface.

    return app
