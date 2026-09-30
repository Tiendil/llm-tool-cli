from pathlib import Path
from typing import Annotated

import pytest
import typer
from typer.core import TyperCommand
from typer.testing import CliRunner

from llm_tool_cli.cli.context import get_global_options, set_global_options
from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol


class TestSetGlobalOptions:
    def test_replaces_options_for_the_invocation(self) -> None:
        root = typer.Context(TyperCommand("root"), obj={"other": "state"})
        child = typer.Context(TyperCommand("child"), parent=root)
        options = GlobalOptions(protocol=Protocol.automation, config_path=ProjectConfigPath(Path("~/custom.toml")))

        set_global_options(root, options)

        assert get_global_options(child) == options
        assert root.obj == {"other": "state"}

        set_global_options(child, GlobalOptions())

        assert get_global_options(root) == GlobalOptions()
        assert root.obj == {"other": "state"}

    def test_nested_commands_and_repeated_invocations(self) -> None:
        app = typer.Typer()
        group = typer.Typer()
        app.add_typer(group, name="nested")
        received: list[GlobalOptions] = []

        @app.callback()
        def initialize(
            context: typer.Context,
            protocol: Annotated[Protocol | None, typer.Option()] = None,
            config: Annotated[Path | None, typer.Option()] = None,
        ) -> None:
            set_global_options(
                context,
                GlobalOptions(protocol=protocol, config_path=None if config is None else ProjectConfigPath(config)),
            )

        @group.command()
        def show(context: typer.Context) -> None:
            received.append(get_global_options(context))

        runner = CliRunner()
        explicit = runner.invoke(app, ["--protocol", "automation", "--config", "~/custom.toml", "nested", "show"])
        unspecified = runner.invoke(app, ["nested", "show"])

        assert explicit.exit_code == 0
        assert unspecified.exit_code == 0
        assert received == [
            GlobalOptions(protocol=Protocol.automation, config_path=ProjectConfigPath(Path("~/custom.toml"))),
            GlobalOptions(),
        ]


class TestGetGlobalOptions:
    @pytest.mark.parametrize("depth", [0, 2])
    def test_missing_options(self, depth: int) -> None:
        context = typer.Context(TyperCommand("root"))
        for _ in range(depth):
            context = typer.Context(TyperCommand("child"), parent=context)

        assert get_global_options(context) == GlobalOptions()
        assert context.find_root().meta == {}

    def test_independent_roots(self) -> None:
        first = typer.Context(TyperCommand("first"))
        second = typer.Context(TyperCommand("second"))
        first_options = GlobalOptions(protocol=Protocol.automation)
        second_options = GlobalOptions(config_path=ProjectConfigPath(Path("other.toml")))
        set_global_options(first, first_options)

        assert get_global_options(second) == GlobalOptions()

        set_global_options(second, second_options)

        assert get_global_options(first) == first_options
        assert get_global_options(second) == second_options
