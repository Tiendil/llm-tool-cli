import datetime
import json
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.output.errors import JournalCommandConfigInvalid, JournalCommandFailed
from llm_tool_cli.output.journal import CommandJournalProcessor, NoopJournalProcessor
from llm_tool_cli.protocol.logic_cells import ContentCell
from llm_tool_cli.protocol.logic_cells.journal import JournalCell


class TestNoopJournalProcessor:
    def test_process__accepts_any_cell_without_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert NoopJournalProcessor().process(ContentCell(kind="empty")).is_ok()
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
        processor.process(cell).unwrap()
        assert json.loads(target.read_text()) == [
            "first\nsecond\rthird",
            timestamp.isoformat(),
            "",
            "literal:{message}",
            "{message",
        ]

    def test_process__supports_non_journal_cell_fields(self, tmp_path: Path) -> None:
        target = tmp_path / "content.txt"
        processor = CommandJournalProcessor(
            [
                sys.executable,
                "-c",
                "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])",
                str(target),
                "{content}",
            ]
        )
        processor.process(
            ContentCell(kind="document", media_type="text/plain", content="  a\nb\n  ", is_journal=True)
        ).unwrap()
        assert target.read_text() == "a\nb"

    @pytest.mark.parametrize("command", [[], ["unused", "{missing}"], ["unused", "{is_journal}"]])
    def test_process__invalid_configuration_does_not_execute(self, mocker: MockerFixture, command: list[str]) -> None:
        run = mocker.patch("llm_tool_cli.output.journal.subprocess.run")
        failures = CommandJournalProcessor(command).process(JournalCell(message="test")).unwrap_err()
        assert isinstance(failures[0], JournalCommandConfigInvalid)
        run.assert_not_called()

    def test_process__missing_executable_is_expected_error(self, tmp_path: Path) -> None:
        command = [str(tmp_path / "missing")]
        error = CommandJournalProcessor(command).process(JournalCell(message="test")).unwrap_err()[0]
        assert isinstance(error, JournalCommandFailed)
        assert error.command == command
        assert error.returncode is None

    @pytest.mark.parametrize("stderr", ["", "explanation"])
    def test_process__nonzero_exit_preserves_context(self, stderr: str) -> None:
        command = [sys.executable, "-c", "import sys; sys.stderr.write(sys.argv[1]); sys.exit(7)", stderr]
        error = CommandJournalProcessor(command).process(JournalCell(message="test")).unwrap_err()[0]
        assert isinstance(error, JournalCommandFailed)
        assert error.returncode == 7
        assert error.command == command
        assert error.details == ("exit code 7; stderr: explanation" if stderr else "exit code 7")
