from enum import StrEnum
from typing import Annotated

import typer

from llm_tool_cli.cli.context import command_context
from llm_tool_cli.output import output
from llm_tool_cli.protocol import cell_shortcuts
from llm_tool_cli.skills import load_skill_text


def register_skill_command(app: typer.Typer, *, package: str, documents: type[StrEnum]) -> None:
    """Register packaged documentation using the consumer's enum, including usage."""

    def skill(
        context: typer.Context,
        document: StrEnum = documents("usage"),
    ) -> None:
        with command_context(context):
            content = load_skill_text(package=package, document=document.value).unwrap()
            output.get().emit([cell_shortcuts.skill(document=document.value, content=content)]).unwrap()

    # Typer reads the consumer's concrete enum for validation, help, and completion.
    skill.__annotations__["document"] = Annotated[documents, typer.Argument()]
    app.command("skill", help="Print built-in skill documentation.")(skill)
