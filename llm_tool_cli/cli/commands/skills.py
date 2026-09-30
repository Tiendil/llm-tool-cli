from enum import StrEnum
from typing import Annotated

import typer

from llm_tool_cli.cli.context import get_global_options
from llm_tool_cli.cli.handling import handle_command_errors
from llm_tool_cli.protocol import cell_shortcuts
from llm_tool_cli.protocol.rendering import write_cells
from llm_tool_cli.skills import load_skill_text


def register_skill_command(app: typer.Typer, *, package: str, documents: type[StrEnum]) -> None:
    """Register packaged documentation using the consumer's enum, including usage."""

    def skill(
        context: typer.Context,
        document: StrEnum = documents("usage"),
    ) -> None:
        protocol = get_global_options(context).protocol_for("skill")
        with handle_command_errors(protocol=protocol):
            content = load_skill_text(package=package, document=document.value).unwrap()
            write_cells([cell_shortcuts.skill(document=document.value, content=content)], protocol=protocol)

    # Typer reads the consumer's concrete enum for validation, help, and completion.
    skill.__annotations__["document"] = Annotated[documents, typer.Argument()]
    app.command("skill", help="Print built-in skill documentation.")(skill)
