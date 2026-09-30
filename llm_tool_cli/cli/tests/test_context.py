import json
from pathlib import Path

import pytest
import typer
from typer.core import TyperCommand
from typer.testing import CliRunner

from llm_tool_cli.cli.context import CommandContext, get_global_options, set_global_options
from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.cli.options import ConfigOption, ProtocolOption
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import info

__all__ = ["isolated_settings"]


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
            protocol: ProtocolOption = None,
            config: ConfigOption = None,
        ) -> None:
            set_global_options(
                context,
                GlobalOptions(protocol=protocol, config_path=config),
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


@pytest.mark.usefixtures("isolated_settings")
class TestCommandContext:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [("skill", Protocol.llm), ("version", Protocol.human), ("alias", Protocol.human), (None, Protocol.human)],
    )
    def test_init__selects_default_for_invoked_name(self, name: str | None, expected: Protocol) -> None:
        context = typer.Context(TyperCommand("different-name"), info_name=name)

        command = CommandContext(context)

        assert command.protocol == expected
        assert command.global_options == GlobalOptions()
        assert context.meta == {}

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_init__uses_root_options_for_nested_command(self, protocol: Protocol) -> None:
        root = typer.Context(TyperCommand("root"))
        group = typer.Context(TyperCommand("group"), parent=root)
        child = typer.Context(TyperCommand("skill"), parent=group, info_name="skill")
        options = GlobalOptions(protocol=protocol, config_path=ProjectConfigPath(Path("~/missing.toml")))
        set_global_options(root, options)

        command = CommandContext(child)

        assert command.protocol == protocol
        assert command.global_options == options
        assert get_global_options(root) == options

    def test_init__keeps_invocations_independent(self) -> None:
        first = typer.Context(TyperCommand("skill"), info_name="skill")
        set_global_options(first, GlobalOptions(protocol=Protocol.automation))
        first_command = CommandContext(first)
        second = typer.Context(TyperCommand("skill"), info_name="skill")

        second_command = CommandContext(second)

        assert first_command.protocol == Protocol.automation
        assert second_command.protocol == Protocol.llm
        assert second_command.global_options == GlobalOptions()

    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("stderr", [False, True])
    def test_write_cells__uses_selected_protocol_and_stream(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, stderr: bool
    ) -> None:
        initialize(tool_label=ToolLabel("TEST"))
        context = typer.Context(TyperCommand("show"), info_name="show")
        set_global_options(context, GlobalOptions(protocol=protocol))
        command = CommandContext(context)
        messages = ["Café", "日本語"]

        command.write_cells((info(message) for message in messages), stderr=stderr)

        captured = capsys.readouterr()
        output, other = (captured.err, captured.out) if stderr else (captured.out, captured.err)
        assert not other
        if protocol == Protocol.automation:
            records = [json.loads(line) for line in output.splitlines()]
            assert [record["content"] for record in records] == messages
        else:
            prefix = "----- TEST CELL " if protocol == Protocol.human else "--TEST-CELL "
            assert output.startswith(prefix)
            assert output.index(messages[0]) < output.index(messages[1])
