from collections.abc import Iterator
from contextlib import contextmanager
from typing import NoReturn

import typer

from llm_tool_cli.core.errors import EnvironmentErrors, exit_code_for_errors
from llm_tool_cli.core.result import UnwrapError
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import environment_error
from llm_tool_cli.protocol.rendering import write_cells


def report_errors_and_exit(errors: EnvironmentErrors, *, protocol: Protocol) -> NoReturn:
    """Render ordered diagnostics to the protocol's error stream and exit."""
    write_cells(
        (environment_error(error) for error in errors),
        protocol=protocol,
        stderr=protocol != Protocol.automation,
    )
    raise typer.Exit(exit_code_for_errors(errors))


@contextmanager
def handle_command_errors(*, protocol: Protocol) -> Iterator[None]:
    """Report failed result unwrapping while leaving unrelated exceptions alone."""
    try:
        yield
    except UnwrapError as error:
        report_errors_and_exit(error.errors, protocol=protocol)
