from pathlib import Path

import pydantic
import tomli

from llm_tool_cli.config import errors


def find_config(filename: str, start_dir: Path) -> Path | None:
    """Find the nearest file from the resolved start directory through its root.

    Matching directories are skipped. No match returns ``None``; filesystem
    failures reported by pathlib raise ``DiscoveryFailed``. The matched file is not read
    or resolved, preserving its containing directory when it is a symlink.
    """
    candidate = start_dir
    try:
        current = start_dir.resolve()
        for directory in (current, *current.parents):
            candidate = directory / filename
            if candidate.is_file():
                return candidate
    except (OSError, RuntimeError) as exc:
        raise errors.DiscoveryFailed(candidate, str(exc)) from exc
    return None


def resolve_config_path(path: Path, cwd: Path) -> Path:
    """Expand an explicit path's home marker, then resolve it against cwd.

    Follow symlinks without requiring the target to exist. Do not search for a
    config or interpret application path syntax. Home expansion and resolution
    failures reported by pathlib raise ``PathResolutionFailed``.
    """
    candidate = path
    try:
        expanded = path.expanduser()
        candidate = expanded if expanded.is_absolute() else cwd / expanded
        return candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise errors.PathResolutionFailed(candidate, str(exc)) from exc


def locate_config(filename: str, *, path: Path | None = None, cwd: Path) -> Path:
    """Select an explicit configuration path or discover the nearest file.

    Explicit paths use ``resolve_config_path`` without falling back to discovery
    or requiring an existing target. Otherwise, search with ``find_config`` and
    raise ``NotFound`` if no match exists. Its ``path`` is the supplied search
    directory and its ``reason`` identifies the filename and search scope.
    Resolution and discovery failures propagate unchanged. No file is read.
    """
    if path is not None:
        return resolve_config_path(path, cwd)

    config_path = find_config(filename, cwd)
    if config_path is None:
        raise errors.NotFound(cwd, f"{filename} was not found in this directory or its parents")
    return config_path


def read_toml(path: Path) -> dict[str, object]:
    """Read UTF-8 TOML 1.1 data without applying an application schema.

    Filesystem, UTF-8, and TOML failures raise ``Unreadable``, ``InvalidEncoding``,
    and ``InvalidToml`` respectively. The supplied path is used without discovery
    or normalization. An empty document returns an empty dictionary.
    """
    try:
        with path.open("rb") as stream:
            return tomli.load(stream)
    except OSError as exc:
        raise errors.Unreadable(path, str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise errors.InvalidEncoding(path, str(exc)) from exc
    except tomli.TOMLDecodeError as exc:
        raise errors.InvalidToml(path, str(exc)) from exc


def load_config[T: pydantic.BaseModel](path: Path, config_class: type[T]) -> T:
    """Read a TOML file and validate it using the caller's Pydantic model.

    Use the supplied path unchanged, without discovery or normalization.
    The model owns its schema, defaults, and validation rules. Read failures
    propagate as documented by ``read_toml``; Pydantic validation failures raise
    ``ValidationFailed`` with the original diagnostic and exception cause.
    Unexpected model failures propagate unchanged.
    """
    raw = read_toml(path)
    try:
        return config_class.model_validate(raw)
    except pydantic.ValidationError as exc:
        raise errors.ValidationFailed(path, str(exc)) from exc


def create_config(path: Path, text: str) -> None:
    """Create a starter from verbatim UTF-8 text, without overwriting any target.

    The parent must already exist. No discovery, path normalization, directory
    creation, or TOML validation occurs. Exclusive creation raises ``AlreadyExists``
    for an existing target, including a symlink. Encoding and other filesystem
    failures raise ``Unwritable``. Failed writes may leave a partial new file.
    """
    try:
        data = text.encode("utf-8")
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError as exc:
        raise errors.AlreadyExists(path, str(exc)) from exc
    except (OSError, UnicodeEncodeError) as exc:
        raise errors.Unwritable(path, str(exc)) from exc
