import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import NoReturn

import typer

from llm_tool_cli.config.runtime import RuntimeConfig, runtime_config
from llm_tool_cli.core.errors import EnvironmentErrors, exit_code_for_errors
from llm_tool_cli.core.result import UnwrapError
from llm_tool_cli.output import OutputEmitter, StreamOutputEmitter, output
from llm_tool_cli.paths import CacheRootPath
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.cell_shortcuts import environment_error


def report_errors_and_exit(
    errors: EnvironmentErrors, *, protocol: Protocol, emitter: OutputEmitter | None = None
) -> NoReturn:
    """Deliver ordered diagnostics through the emitter and exit."""
    emitter = emitter if emitter is not None else StreamOutputEmitter()
    # Early diagnostics never use the cache. The null device is an unused path
    # placeholder, without discovery, resolution, or filesystem access.
    selected = (
        runtime_config.get().replace(protocol=protocol)
        if runtime_config.is_set()
        else RuntimeConfig(protocol=protocol, cache_dir=CacheRootPath(Path(os.devnull)))
    )
    with runtime_config.scope(selected):
        emitter.discard()
        emitter.emit([environment_error(error) for error in errors]).unwrap()
        emitter.flush()
    raise typer.Exit(exit_code_for_errors(errors))


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
