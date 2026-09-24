"""Public configuration failures.

Concrete ``code`` values are stable compatibility identifiers. Callers may inspect
the returned values without parsing messages. ``path`` identifies the
failed operation's filesystem input; ``reason`` contains the original reason.
The producing operation preserves any underlying low-level exception as ``cause``.
"""

from pathlib import Path

from llm_tool_cli.core import errors as core_errors


class EnvironmentError(core_errors.EnvironmentError):
    """Classification and filesystem context for configuration failures."""

    path: Path
    reason: str
    message: str = "{error.path}: {error.reason}"


class PathResolutionFailed(EnvironmentError):
    """An explicit path could not be resolved."""

    code: str = "config_path_resolution_failed"


class DiscoveryFailed(EnvironmentError):
    """The search directory or a candidate could not be inspected."""

    code: str = "config_discovery_failed"


class NotFound(EnvironmentError):
    """No configuration file was found in the search directory or its parents."""

    code: str = "config_not_found"


class Unreadable(EnvironmentError):
    """A configuration file could not be opened or read."""

    code: str = "config_unreadable"


class InvalidEncoding(EnvironmentError):
    """A configuration file does not contain valid UTF-8."""

    code: str = "config_invalid_encoding"


class InvalidToml(EnvironmentError):
    """A configuration file does not contain valid TOML."""

    code: str = "config_invalid_toml"


class ValidationFailed(EnvironmentError):
    """Parsed configuration does not satisfy the supplied model."""

    code: str = "config_validation_failed"


class AlreadyExists(EnvironmentError):
    """The starter target already exists and was left untouched."""

    code: str = "config_already_exists"


class Unwritable(EnvironmentError):
    """Starter text could not be encoded or written to the target."""

    code: str = "config_unwritable"
