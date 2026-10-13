import datetime
import subprocess  # noqa: S404
from typing import Protocol

from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.output.errors import JournalCommandConfigInvalid, JournalCommandFailed
from llm_tool_cli.protocol.logic_cells.base import LogicCell


class JournalProcessor(Protocol):
    __slots__ = ()

    def process(self, cell: LogicCell) -> Result[None]: ...  # noqa: E704


class NoopJournalProcessor:
    __slots__ = ()

    def process(self, cell: LogicCell) -> Result[None]:
        return Ok(None)


class CommandJournalProcessor:
    """Forward logical fields as whole arguments, without a shell or text flattening."""

    __slots__ = ("command",)

    def __init__(self, command: list[str]) -> None:
        self.command = tuple(command)

    def process(self, cell: LogicCell) -> Result[None]:  # noqa: CCR001
        if not self.command:
            return Err([JournalCommandConfigInvalid(argument="", details="Configured command is empty.")])

        fields = cell.model_dump(mode="python")
        args = []
        for argument in self.command:
            if len(argument) >= 2 and argument.startswith("{") and argument.endswith("}"):
                name = argument[1:-1]
                if name not in fields:
                    return Err(
                        [JournalCommandConfigInvalid(argument=argument, details=f"Unknown cell field `{name}`.")]
                    )
                value = fields[name]
                if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
                    argument = value.isoformat()
                else:
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
