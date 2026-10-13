import datetime
import json
import sys
from pathlib import Path

import pydantic
import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.output.errors import JournalCommandConfigInvalid, JournalCommandFailed
from llm_tool_cli.output.journal import CommandJournalProcessor, JournalConfig, NoopJournalProcessor
from llm_tool_cli.protocol.journal import JournalRecord
from llm_tool_cli.protocol.logic_cells import EnvironmentErrorCell
from llm_tool_cli.protocol.logic_cells.journal import JournalCell


class TestNoopJournalProcessor:
    def test_process__accepts_record_without_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert NoopJournalProcessor().process(JournalRecord(message="event")).is_ok()
        assert capsys.readouterr() == ("", "")


class TestCommandJournalProcessor:
    def test_process__preserves_literal_and_multiline_arguments(self, tmp_path: Path) -> None:
        target = tmp_path / "arguments.json"
        timestamp = datetime.datetime.now(datetime.UTC)
        cell = JournalCell(message="  first\nsecond\rthird  ", timestamp=timestamp)
        processor = CommandJournalProcessor(
            [
                sys.executable,
                "-c",
                "import json, pathlib, sys; pathlib.Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))",
                str(target),
                "{message}",
                "{timestamp}",
                "{actor_id}",
                "literal:{message}",
                "{message",
            ]
        )
        processor.process(cell.to_journal_record()).unwrap()
        assert json.loads(target.read_text()) == [
            "first\nsecond\rthird",
            timestamp.isoformat(),
            "",
            "literal:{message}",
            "{message",
        ]

    def test_process__supports_error_cell_fields(self, tmp_path: Path) -> None:
        target = tmp_path / "code.txt"
        processor = CommandJournalProcessor(
            [
                sys.executable,
                "-c",
                "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])",
                str(target),
                "{code}",
            ]
        )
        processor.process(
            EnvironmentErrorCell(error=EnvironmentError(code="failed", message="failure")).to_journal_record()
        ).unwrap()
        assert target.read_text() == "failed"

    def test_process__empty_command_does_not_execute(self, mocker: MockerFixture) -> None:
        run = mocker.patch("llm_tool_cli.output.journal.subprocess.run")
        failures = CommandJournalProcessor([]).process(JournalRecord(message="test")).unwrap_err()
        assert isinstance(failures[0], JournalCommandConfigInvalid)
        run.assert_not_called()

    def test_process__missing_executable_is_expected_error(self, tmp_path: Path) -> None:
        command = [str(tmp_path / "missing")]
        error = CommandJournalProcessor(command).process(JournalRecord(message="test")).unwrap_err()[0]
        assert isinstance(error, JournalCommandFailed)
        assert error.command == command
        assert error.returncode is None

    @pytest.mark.parametrize("stderr", ["", "explanation"])
    def test_process__nonzero_exit_preserves_context(self, stderr: str) -> None:
        command = [sys.executable, "-c", "import sys; sys.stderr.write(sys.argv[1]); sys.exit(7)", stderr]
        error = CommandJournalProcessor(command).process(JournalRecord(message="test")).unwrap_err()[0]
        assert isinstance(error, JournalCommandFailed)
        assert error.returncode == 7
        assert error.command == command
        assert error.details == ("exit code 7; stderr: explanation" if stderr else "exit code 7")

    @pytest.mark.parametrize(
        "attributes, expected",
        [
            ({}, ""),
            ({"task_id": None}, ""),
            ({"task_id": "T-1"}, "T-1"),
            ({"task_id": 0}, "0"),
            ({"task_id": False}, "False"),
        ],
    )
    def test_process__substitutes_record_fields(
        self, tmp_path: Path, attributes: dict[str, pydantic.JsonValue], expected: str
    ) -> None:
        target = tmp_path / "argument.txt"
        processor = CommandJournalProcessor(
            [
                sys.executable,
                "-c",
                "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])",
                str(target),
                "{task_id}",
            ]
        )
        processor.process(JournalRecord(message="event", attributes=attributes)).unwrap()
        assert target.read_text() == expected


class TestJournalConfig:
    @pytest.mark.parametrize("command", [[], ["tool", 1]])
    def test_validation__rejects_invalid_command(self, command: list[object]) -> None:
        with pytest.raises(pydantic.ValidationError):
            JournalConfig.model_validate({"cmd": command})

    def test_processor__defaults_to_noop(self) -> None:
        assert JournalConfig().processor().process(JournalRecord(message="event")).is_ok()

    def test_processor__uses_record_fields_without_declarations(self, tmp_path: Path) -> None:
        target = tmp_path / "arguments.json"
        config = JournalConfig(
            cmd=[
                sys.executable,
                "-c",
                "import json, pathlib, sys; pathlib.Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))",
                str(target),
                "{missing}",
                "{message}",
                "{custom_field}",
                "{attributes}",
                "after",
            ]
        )
        config.processor().process(JournalRecord(message="event", attributes={"custom_field": "value"})).unwrap()
        assert json.loads(target.read_text()) == ["", "event", "value", "", "after"]
