import json
from pathlib import Path

import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.commands.tests.make import cache_app
from llm_tool_cli.config.project import project_config
from llm_tool_cli.config.runtime import runtime_config
from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.core.errors import EnvironmentErrors
from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.core.settings import initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.output import StreamOutputEmitter, output
from llm_tool_cli.protocol.tests.helpers import cell_payloads
from llm_tool_cli.tool_cache import ToolCache, errors
from llm_tool_cli.tool_cache.tests.helpers import cached_entry
from llm_tool_cli.tool_cache.tests.make import cache_storage

__all__ = ["isolated_settings"]


@pytest.mark.usefixtures("isolated_settings")
class TestRegisterCacheCleanCommand:
    @pytest.fixture(autouse=True)
    def initialize_settings(self, isolated_settings: None) -> None:
        initialize(name=ToolName("test"))

    @pytest.mark.parametrize("group_name", [None, "objects"])
    @pytest.mark.parametrize("protocol", [None, "human", "llm", "automation"])
    def test_cleans_on_supplied_app_and_reports_repeated_invocations(  # noqa: CCR001 — Protocol and outcome cases.
        self, tmp_path: Path, group_name: str | None, protocol: str | None
    ) -> None:
        root = tmp_path / "cache"
        entry = cached_entry(root)
        app = cache_app(lambda context: Ok(cache_storage(root)), group_name=group_name)
        config = tmp_path / "config.toml"
        config.write_text("malformed[")
        options = [] if protocol is None else ["-p", protocol]
        command = ["clean"] if group_name is None else [group_name, "clean"]

        for outcome in ("cleaned", "unchanged"):
            result = CliRunner().invoke(app, [*options, "--config", str(config), *command])
            assert result.exit_code == 0, result.output
            assert not result.stderr
            if protocol == "automation":
                assert cell_payloads([json.loads(result.stdout)]) == [
                    {
                        "type": "cache",
                        "operation": "clean",
                        "cache_dir": str(root),
                        "outcome": outcome,
                        "content": None,
                    }
                ]
            else:
                assert outcome in result.stdout
                assert str(root) in result.stdout
                if protocol == "llm":
                    assert "--TEST-CELL " in result.stdout
            assert not entry.exists()
            assert (root / "cache.lock").is_file()
            assert config.read_text() == "malformed["
            assert not project_config.is_set()
            assert not runtime_config.is_set()
            assert not output.is_set()

    def test_absent_cache_stays_absent(self, tmp_path: Path) -> None:
        root = tmp_path / "missing"
        app = cache_app(lambda context: Ok(cache_storage(root)))
        result = CliRunner().invoke(app, ["-p", "automation", "objects", "clean"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["outcome"] == "unchanged"
        assert not root.exists()

    @pytest.mark.parametrize(
        ("arguments", "exit_code"),
        [
            (["--help"], 0),
            (["objects"], 2),
            (["objects", "--help"], 0),
            (["objects", "clean", "--help"], 0),
            (["objects", "clean", "extra"], 2),
            (["objects", "clean", "--unknown"], 2),
            (["cache", "clean"], 2),
        ],
    )
    def test_registration_help_and_parsing_do_not_call_factory(self, arguments: list[str], exit_code: int) -> None:
        def unexpected(context: typer.Context) -> Result[ToolCache]:
            raise AssertionError("Cache selection is only for command execution.")

        app = cache_app(unexpected)
        result = CliRunner().invoke(app, arguments)
        assert result.exit_code == exit_code, result.output

    @pytest.mark.parametrize("stage", ["factory", "clean"])
    @pytest.mark.parametrize("protocol", ["human", "llm", "automation"])
    def test_propagates_failures_without_success_and_restores_resources(
        self, tmp_path: Path, mocker: MockerFixture, stage: str, protocol: str
    ) -> None:
        binding = ContextValue[Path]("cache-test")
        cause = PermissionError("unreadable")
        problems: EnvironmentErrors = [
            errors.AccessFailed(path=tmp_path, reason="unreadable").with_cause(cause),
            errors.AccessFailed(path=tmp_path / "second", reason="also unreadable"),
        ]

        def factory(context: typer.Context) -> Result[ToolCache]:
            context.with_resource(binding.scope(tmp_path))
            return Err(problems) if stage == "factory" else Ok(cache_storage(tmp_path))

        if stage == "clean":
            mocker.patch.object(ToolCache, "clean", return_value=Err(problems))

        original_flush = StreamOutputEmitter.flush

        def flush(emitter: StreamOutputEmitter) -> None:
            assert binding.get() == tmp_path
            original_flush(emitter)

        mocker.patch.object(StreamOutputEmitter, "flush", flush)
        result = CliRunner().invoke(cache_app(factory), ["-p", protocol, "objects", "clean"])
        assert result.exit_code == 3
        assert not result.stderr
        if protocol == "automation":
            records = cell_payloads([json.loads(line) for line in result.stdout.splitlines()])
            assert len(records) == len(problems)
            for record, problem in zip(records, problems):
                expected = problem.as_record()
                content = record.pop("content")
                assert isinstance(content, str)
                assert content.startswith(str(expected.pop("message")))
                assert "Way" in content
                assert record == expected
        else:
            assert "unreadable" in result.stdout
            assert "unchanged" not in result.stdout
        assert problems[0].cause == cause
        assert not binding.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()

    def test_unexpected_factory_failure_propagates_and_restores_resources(self, tmp_path: Path) -> None:
        binding = ContextValue[Path]("cache-test")

        def factory(context: typer.Context) -> Result[ToolCache]:
            context.with_resource(binding.scope(tmp_path))
            raise RuntimeError("factory failed")

        result = CliRunner().invoke(cache_app(factory), ["-p", "automation", "objects", "clean"])
        assert isinstance(result.exception, RuntimeError)
        assert not result.stdout
        assert not binding.is_set()
        assert not runtime_config.is_set()
        assert not output.is_set()
