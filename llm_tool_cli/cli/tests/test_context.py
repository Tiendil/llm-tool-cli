import io
import json
from pathlib import Path

import pytest
import typer
from typer.core import TyperCommand
from typer.testing import CliRunner

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.context import CommandContext, command_context
from llm_tool_cli.cli.errors import InvalidArguments
from llm_tool_cli.config.project import ProjectConfig, project_config
from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core.result import UnwrapError
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.output import StreamOutputEmitter
from llm_tool_cli.output import output as active_output
from llm_tool_cli.output.tests.helpers import CollectingEmitter
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import info, operation_succeeded
from llm_tool_cli.protocol.logic_cells.base import LogicCell
from llm_tool_cli.protocol.logic_cells.warning import WarningCell

__all__ = ["isolated_settings"]


@pytest.mark.usefixtures("isolated_settings")
class TestCommandContext:
    def test_command_scope_without_project_flushes_and_restores_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        previous = CollectingEmitter()
        with active_output.scope(previous):
            with typer.Context(TyperCommand("show")) as context:
                with command_context(context):
                    assert not project_config.is_set()
                    active_output.get().emit([info("Without a project")]).unwrap()
                    assert not capsys.readouterr().out
                assert "Without a project" in capsys.readouterr().out
            assert active_output.get() == previous
        assert not previous.cells
        assert not active_output.is_set()
        assert not runtime_config.is_set()

    @pytest.mark.parametrize(
        "failure, exit_code, record_types",
        [
            (None, 0, ["operation_succeeded", "warning"]),
            (UnwrapError(error=[InvalidArguments(reason="Invalid input")]), 1, ["error", "warning"]),
            (RuntimeError("Unexpected failure"), 1, []),
            (typer.Exit(7), 7, []),
        ],
    )
    def test_command_scope_finalizes_using_active_emitter_before_framework_cleanup(
        self, tmp_path: Path, failure: Exception | None, exit_code: int, record_types: list[str]
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        project = ProjectConfig(config_path=ProjectConfigPath(tmp_path / "active.toml"))
        stream = io.StringIO()
        rendered: list[list[LogicCell]] = []

        class ProjectEmitter(StreamOutputEmitter):
            def _render(self, cells: list[LogicCell]) -> str:
                assert project_config.get() == project
                assert runtime_config.get().protocol == Protocol.automation
                rendered.append(cells)
                return super()._render(cells)

        app = create_app(help="Exercise command finalization.")

        @app.command()
        def show(context: typer.Context) -> None:
            with command_context(context):
                context.with_resource(project_config.scope(project))
                context.with_resource(active_output.scope(ProjectEmitter(stream=stream)))
                active_output.get().emit([WarningCell(message="A warning")]).unwrap()
                active_output.get().emit([operation_succeeded("Completed")]).unwrap()
                assert not stream.getvalue()
                if failure is not None:
                    raise failure

        previous_output = CollectingEmitter()
        previous_runtime = RuntimeConfig(protocol=Protocol.llm)
        previous_project = ProjectConfig(config_path=ProjectConfigPath(tmp_path / "outer.toml"))
        with (
            active_output.scope(previous_output),
            runtime_config.scope(previous_runtime),
            project_config.scope(previous_project),
        ):
            result = CliRunner().invoke(app, ["-p", "automation", "show"])
            assert active_output.get() == previous_output
            assert runtime_config.get() == previous_runtime
            assert project_config.get() == previous_project

        assert result.exit_code == exit_code, result.exception
        assert not result.stdout
        assert not result.stderr
        assert [json.loads(line)["type"] for line in stream.getvalue().splitlines()] == record_types
        assert bool(rendered) == bool(record_types)
        assert not previous_output.cells
        if failure is not None and not isinstance(failure, (typer.Exit, UnwrapError)):
            assert result.exception == failure

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
    @pytest.mark.parametrize("custom_stream", [False, True])
    def test_init__binds_output_with_selected_protocol_and_supports_stream_override(
        self, capsys: pytest.CaptureFixture[str], protocol: Protocol, custom_stream: bool
    ) -> None:
        initialize(label=ToolLabel("TEST"))
        messages = ["Café", "日本語"]
        stream = io.StringIO()

        with typer.Context(TyperCommand("show"), info_name="show") as context:
            context.params["protocol"] = protocol
            CommandContext(context)
            if custom_stream:
                context.with_resource(active_output.scope(StreamOutputEmitter(stream=stream)))
            active_output.get().emit([info(message) for message in messages]).unwrap()
            assert capsys.readouterr() == ("", "")
            assert not stream.getvalue()
            active_output.get().flush()

        captured = capsys.readouterr()
        output = stream.getvalue() if custom_stream else captured.out
        assert not (captured.out if custom_stream else stream.getvalue())
        assert not captured.err
        if protocol == Protocol.automation:
            records = [json.loads(line) for line in output.splitlines()]
            assert [record["content"] for record in records] == messages
        else:
            prefix = "----- TEST CELL " if protocol == Protocol.human else "--TEST-CELL "
            assert output.startswith(prefix)
            assert output.index(messages[0]) < output.index(messages[1])
