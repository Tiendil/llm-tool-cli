import subprocess  # noqa: S404
from typing import Protocol

import pydantic

from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.output.errors import JournalCommandConfigInvalid, JournalCommandFailed
from llm_tool_cli.protocol.journal import JournalRecord


class JournalProcessor(Protocol):
    __slots__ = ()

    def process(self, record: JournalRecord) -> Result[None]: ...  # noqa: E704


class NoopJournalProcessor:
    __slots__ = ()

    def process(self, record: JournalRecord) -> Result[None]:
        return Ok(None)


class CommandJournalProcessor:
    """Forward record fields as whole arguments, without a shell or text flattening."""

    __slots__ = ("command",)

    def __init__(self, command: list[str]) -> None:
        self.command = tuple(command)

    def process(self, record: JournalRecord) -> Result[None]:  # noqa: CCR001
        if not self.command:
            return Err([JournalCommandConfigInvalid(argument="", details="Configured command is empty.")])

        fields = record.as_dict()
        args = []
        for argument in self.command:
            if len(argument) >= 2 and argument.startswith("{") and argument.endswith("}"):
                value = fields.get(argument[1:-1])
                argument = "" if value is None else str(value)
            args.append(argument)

        try:
            result = subprocess.run(args, check=False, capture_output=True, text=True)  # noqa: S603
        except OSError as error:
            return Err([JournalCommandFailed(command=args, returncode=None, details=str(error))])

        if result.returncode:
            details = f"exit code {result.returncode}"
            if result.stderr.strip():
                details += f"; stderr: {result.stderr.strip()}"
            return Err([JournalCommandFailed(command=args, returncode=result.returncode, details=details)])
        return Ok(None)


class JournalConfig(BaseEntity):
    """Optional external command forwarding."""

    cmd: list[str] | None = pydantic.Field(default=None, min_length=1)

    def processor(self) -> JournalProcessor:
        if self.cmd is None:
            return NoopJournalProcessor()
        return CommandJournalProcessor(self.cmd)
