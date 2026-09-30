import typer


def create_app(*, help: str) -> typer.Typer:
    return typer.Typer(
        help=help,
        add_completion=True,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
