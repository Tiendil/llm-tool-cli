from pathlib import Path
from typing import Annotated

import typer

from llm_tool_cli.paths import ProjectConfigPath


def _parse_config_path(value: str) -> ProjectConfigPath:
    return ProjectConfigPath(Path(value))


ConfigOption = Annotated[
    ProjectConfigPath | None,
    typer.Option(
        "--config",
        parser=_parse_config_path,
        metavar="PATH",
        help="Configuration file path. Overrides the command's default configuration location.",
    ),
]
