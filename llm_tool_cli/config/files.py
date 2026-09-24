from pathlib import Path

import pydantic
import tomli

from llm_tool_cli.config import errors
from llm_tool_cli.core.errors import EnvironmentErrors
from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error


def find_config(filename: str, start_dir: Path) -> Result[Path | None, EnvironmentErrors]:
    """Find the nearest file from the resolved start directory through its root.

    Matching directories are skipped. No match returns ``Ok(None)``; filesystem
    failures reported by pathlib return ``Err([DiscoveryFailed(...)])``. The matched file is not read
    or resolved, preserving its containing directory when it is a symlink.
    """
    candidate = start_dir
    try:
        current = start_dir.resolve()
        for directory in (current, *current.parents):
            candidate = directory / filename
            if candidate.is_file():
                return Ok(candidate)
    except (OSError, RuntimeError) as exc:
        return Err([errors.DiscoveryFailed(path=candidate, reason=str(exc)).with_cause(exc)])
    return Ok(None)


def resolve_config_path(path: Path, cwd: Path) -> Result[Path, EnvironmentErrors]:
    """Expand an explicit path's home marker, then resolve it against cwd.

    Follow symlinks without requiring the target to exist. Do not search for a
    config or interpret application path syntax. Home expansion and resolution
    failures reported by pathlib return ``Err([PathResolutionFailed(...)])``.
    """
    candidate = path
    try:
        expanded = path.expanduser()
        candidate = expanded if expanded.is_absolute() else cwd / expanded
        return Ok(candidate.resolve())
    except (OSError, RuntimeError) as exc:
        return Err([errors.PathResolutionFailed(path=candidate, reason=str(exc)).with_cause(exc)])


@unwrap_to_error
def locate_config(filename: str, *, path: Path | None = None, cwd: Path) -> Result[Path, EnvironmentErrors]:
    """Select an explicit configuration path or discover the nearest file.

    Explicit paths use ``resolve_config_path`` without falling back to discovery
    or requiring an existing target. Otherwise, search with ``find_config`` and
    return ``Err([NotFound(...)])`` if no match exists. Its ``path`` is the supplied search
    directory and its ``reason`` identifies the filename and search scope.
    Resolution and discovery failures propagate unchanged. No file is read.
    """
    if path is not None:
        return resolve_config_path(path, cwd)

    config_path = find_config(filename, cwd).unwrap()
    if config_path is None:
        return Err([errors.NotFound(path=cwd, reason=f"{filename} was not found in this directory or its parents")])
    return Ok(config_path)


def read_toml(path: Path) -> Result[dict[str, object], EnvironmentErrors]:
    """Read UTF-8 TOML 1.1 data without applying an application schema.

    Filesystem, UTF-8, and TOML failures return ``Unreadable``, ``InvalidEncoding``,
    and ``InvalidToml`` in error lists respectively. The supplied path is used without discovery
    or normalization. An empty document returns ``Ok({})``.
    """
    try:
        with path.open("rb") as stream:
            return Ok(tomli.load(stream))
    except OSError as exc:
        return Err([errors.Unreadable(path=path, reason=str(exc)).with_cause(exc)])
    except UnicodeDecodeError as exc:
        return Err([errors.InvalidEncoding(path=path, reason=str(exc)).with_cause(exc)])
    except tomli.TOMLDecodeError as exc:
        return Err([errors.InvalidToml(path=path, reason=str(exc)).with_cause(exc)])


@unwrap_to_error
def load_config[T: pydantic.BaseModel](path: Path, config_class: type[T]) -> Result[T, EnvironmentErrors]:
    """Read a TOML file and validate it using the caller's Pydantic model.

    Use the supplied path unchanged, without discovery or normalization.
    The model owns its schema, defaults, and validation rules. Read failures
    propagate as documented by ``read_toml``; Pydantic validation failures return
    ``Err([ValidationFailed(...)])`` with diagnostic text and the original exception cause.
    Unexpected model failures propagate unchanged.
    """
    raw = read_toml(path).unwrap()
    try:
        return Ok(config_class.model_validate(raw))
    except pydantic.ValidationError as exc:
        return Err([errors.ValidationFailed(path=path, reason=str(exc)).with_cause(exc)])


def create_config(path: Path, text: str) -> Result[None, EnvironmentErrors]:
    """Create a starter from verbatim UTF-8 text, without overwriting any target.

    The parent must already exist. No discovery, path normalization, directory
    creation, or TOML validation occurs. Exclusive creation returns ``AlreadyExists``
    for an existing target, including a symlink. Encoding and other filesystem
    failures return ``Unwritable``. Failures are carried in error lists; success is
    ``Ok(None)``. Failed writes may leave a partial new file.
    """
    try:
        data = text.encode("utf-8")
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError as exc:
        return Err([errors.AlreadyExists(path=path, reason=str(exc)).with_cause(exc)])
    except (OSError, UnicodeEncodeError) as exc:
        return Err([errors.Unwritable(path=path, reason=str(exc)).with_cause(exc)])
    return Ok(None)
