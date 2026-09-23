"""Configuration file mechanics independent of application schemas and defaults.

The four exported operations and ``config.errors`` are public interfaces.
Callers own filenames, home expansion, template resources, schema validation,
workspace construction, and presentation of failures.
"""

from llm_tool_cli.config.files import create_config, find_config, read_toml, resolve_config_path

__all__ = ["create_config", "find_config", "read_toml", "resolve_config_path"]
