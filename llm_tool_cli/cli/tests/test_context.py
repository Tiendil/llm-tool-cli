import json
from pathlib import Path

import pytest
import typer
from typer.core import TyperCommand

from llm_tool_cli.cli.context import CommandContext
from llm_tool_cli.config.project import project_config
from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import info

__all__ = ["isolated_settings"]


@pytest.mark.usefixtures("isolated_settings")
class TestCommandContext:
    def test_init__nested_skill_uses_leaf_command_default(self) -> None:
        with typer.Context(TyperCommand("root")) as root:
            with typer.Context(TyperCommand("group"), parent=root) as group:
                with typer.Context(TyperCommand("skill"), parent=group, info_name="skill") as context:
                    assert CommandContext(context).protocol == Protocol.llm

    @pytest.mark.parametrize(
        ("name", "expected"),
        [("skill", Protocol.llm), ("version", Protocol.human), ("alias", Protocol.human), (None, Protocol.human)],
    )
    def test_init__selects_default_for_invoked_name(self, name: str | None, expected: Protocol) -> None:
        with typer.Context(TyperCommand("different-name"), info_name=name) as context:
            command = CommandContext(context)
            assert command.protocol == expected
            assert command.config_input is None
            assert not project_config.is_set()
            assert context.meta == {}
        assert not runtime_config.is_set()

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_init__uses_root_inputs_for_nested_command(self, protocol: Protocol) -> None:
        with typer.Context(TyperCommand("root")) as root:
            root.params.update(protocol=protocol, config_path=ProjectConfigPath(Path("~/missing.toml")))
            with typer.Context(TyperCommand("group"), parent=root) as group:
                with typer.Context(TyperCommand("skill"), parent=group, info_name="skill") as child:
                    command = CommandContext(child)
                    assert command.protocol == protocol
                    assert command.config_input == Path("~/missing.toml")
                    assert not project_config.is_set()
        assert not runtime_config.is_set()

    def test_protocol__reads_current_runtime_instead_of_retaining_a_copy(self) -> None:
        with typer.Context(TyperCommand("show"), info_name="show") as context:
            context.params["protocol"] = Protocol.automation
            command = CommandContext(context)
            observed = [command.protocol]
            with runtime_config.scope(RuntimeConfig(protocol=Protocol.llm)):
                observed.append(command.protocol)
            observed.append(command.protocol)
            assert observed == [Protocol.automation, Protocol.llm, Protocol.automation]

    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("stderr", [False, True])
    def test_write_cells__uses_selected_protocol_and_stream(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, stderr: bool
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        messages = ["Café", "日本語"]

        with typer.Context(TyperCommand("show"), info_name="show") as context:
            context.params["protocol"] = protocol
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
