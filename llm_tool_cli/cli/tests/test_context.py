import json
from pathlib import Path

import pytest
import typer
from typer.core import TyperCommand

from llm_tool_cli.cli.context import CommandContext, global_options
from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import info

__all__ = ["isolated_settings"]


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
        assert not global_options.is_set()
        assert context.meta == {}

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_init__uses_active_options_for_nested_command(self, protocol: Protocol) -> None:
        root = typer.Context(TyperCommand("root"))
        group = typer.Context(TyperCommand("group"), parent=root)
        child = typer.Context(TyperCommand("skill"), parent=group, info_name="skill")
        options = GlobalOptions(protocol=protocol, config_path=ProjectConfigPath(Path("~/missing.toml")))
        with global_options.scope(options):
            command = CommandContext(child)

        assert command.protocol == protocol
        assert command.global_options == options
        assert options == GlobalOptions(protocol=protocol, config_path=ProjectConfigPath(Path("~/missing.toml")))

    def test_init__keeps_scopes_independent(self) -> None:
        first = typer.Context(TyperCommand("skill"), info_name="skill")
        with global_options.scope(GlobalOptions(protocol=Protocol.automation)):
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
        initialize(label=ToolLabel("TEST"))
        context = typer.Context(TyperCommand("show"), info_name="show")
        messages = ["Café", "日本語"]

        with global_options.scope(GlobalOptions(protocol=protocol)):
            command = CommandContext(context)
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
