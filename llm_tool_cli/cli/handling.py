from collections.abc import Iterator
from contextlib import contextmanager
from typing import NoReturn

import typer

from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core.errors import EnvironmentErrors, exit_code_for_errors
from llm_tool_cli.core.result import UnwrapError
from llm_tool_cli.output import OutputEmitter, StreamOutputEmitter, output
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import environment_error


def report_errors_and_exit(
    errors: EnvironmentErrors, *, protocol: Protocol, emitter: OutputEmitter | None = None
) -> NoReturn:
    """Deliver ordered diagnostics through the emitter and exit."""
    # Parsing can fail before command setup has established runtime/output scopes.
    emitter = emitter if emitter is not None else StreamOutputEmitter()
    delivery_errors: EnvironmentErrors = []
    with runtime_config.scope(RuntimeConfig(protocol=protocol)):
        emitter.discard()
        for error in errors:
            cell = environment_error(error).replace(is_journal=True)
            delivered = emitter.emit([cell])
            if delivered.is_err():
                delivery_errors.extend(delivered.unwrap_err())
                # Journal forwarding is disabled; preserve this diagnostic in its original position.
                emitter.emit([cell]).unwrap()
        emitter.emit([environment_error(error) for error in delivery_errors]).unwrap()
        emitter.flush()
    raise typer.Exit(exit_code_for_errors([*errors, *delivery_errors]))


@contextmanager
def handle_command_errors(*, protocol: Protocol) -> Iterator[None]:
    """Report failed result unwrapping while leaving unrelated exceptions alone."""
    try:
        yield
    except UnwrapError as error:
        report_errors_and_exit(error.errors, protocol=protocol, emitter=output.get() if output.is_set() else None)
    except BaseException:
        if output.is_set():
            output.get().discard()
        raise
    else:
        if output.is_set():
            output.get().flush()
