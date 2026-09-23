from pathlib import Path

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
    """Resolve an explicit path, using cwd only for a relative path.

    Follow symlinks without requiring the target to exist. Do not search for a
    config, expand home markers, or interpret application path syntax.
    Resolution failures reported by pathlib raise ``PathResolutionFailed``.
    """
    candidate = path if path.is_absolute() else cwd / path
    try:
        return candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise errors.PathResolutionFailed(candidate, str(exc)) from exc


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
