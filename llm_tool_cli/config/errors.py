"""Public configuration failures.

Concrete ``code`` values are stable compatibility identifiers. Callers may catch
the corresponding classes without parsing messages. ``path`` identifies the
failed operation's filesystem input; ``reason`` contains the original reason.
The producing operation preserves any underlying low-level exception through chaining.
"""

from pathlib import Path

from llm_tool_cli.core import errors as core_errors


class Error(core_errors.Error):
    """Classification and filesystem context for configuration failures."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")

    def as_record(self) -> dict[str, object]:
        return {**super().as_record(), "path": str(self.path), "reason": self.reason}


class PathResolutionFailed(Error):
    """An explicit path could not be resolved."""

    code = "config_path_resolution_failed"


class DiscoveryFailed(Error):
    """The search directory or a candidate could not be inspected."""

    code = "config_discovery_failed"


class NotFound(Error):
    """No configuration file was found in the search directory or its parents."""

    code = "config_not_found"


class Unreadable(Error):
    """A configuration file could not be opened or read."""

    code = "config_unreadable"


class InvalidEncoding(Error):
    """A configuration file does not contain valid UTF-8."""

    code = "config_invalid_encoding"


class InvalidToml(Error):
    """A configuration file does not contain valid TOML."""

    code = "config_invalid_toml"


class ValidationFailed(Error):
    """Parsed configuration does not satisfy the supplied model."""

    code = "config_validation_failed"


class AlreadyExists(Error):
    """The starter target already exists and was left untouched."""

    code = "config_already_exists"


class Unwritable(Error):
    """Starter text could not be encoded or written to the target."""

    code = "config_unwritable"
