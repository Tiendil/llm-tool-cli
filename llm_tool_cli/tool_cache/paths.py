from pathlib import Path

from platformdirs import user_cache_path

from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.core.result import Err, Ok, Result, unwrap_to_error
from llm_tool_cli.paths import resolve_project_root
from llm_tool_cli.tool_cache import errors
from llm_tool_cli.tool_cache.entities import CacheRootPath


def _default_cache_root(name: ToolName) -> Result[Path]:
    try:
        location = user_cache_path(name, appauthor=False, opinion=False, ensure_exists=False)
        if location.is_absolute():
            return Ok(location)
    except (OSError, RuntimeError):
        pass
    try:
        return Ok(Path.home() / ".cache" / name)
    except (OSError, RuntimeError) as exc:
        return Err([errors.AccessFailed(path=Path("."), reason=str(exc)).with_cause(exc)])


@unwrap_to_error
def resolve_cache_root(name: ToolName, value: Path | None, *, cwd: Path) -> Result[CacheRootPath]:
    """Resolve an override or the platform cache location, without creating it.

    Relative overrides use cwd; home markers expand. Only unavailable default
    discovery falls back to ~/.cache/<name>. Unusable explicit paths never fall
    back to another directory.
    """
    try:
        selected = _default_cache_root(name).unwrap() if value is None else value
        expanded = selected.expanduser()
    except (OSError, RuntimeError) as exc:
        return Err([errors.AccessFailed(path=cwd, reason=str(exc)).with_cause(exc)])
    path = resolve_project_root(expanded if expanded.is_absolute() else cwd / expanded).unwrap()
    return Ok(CacheRootPath(path))
