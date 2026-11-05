from pathlib import Path

from llm_tool_cli.paths import PathSegment
from llm_tool_cli.tool_cache import CacheIdentity
from llm_tool_cli.tool_cache.tests.make import cache_storage


def cached_entry(root: Path, *, namespace: str = "objects", key: str = "https://host/shared") -> Path:
    with cache_storage(root).entry(CacheIdentity(namespace=PathSegment(namespace), key=key)) as result:
        entry = result.unwrap()
        payload = entry / "payload" / "versions"
        payload.mkdir(parents=True)
        (payload / "first").write_bytes(b"cached first revision")
        (payload / "second").write_bytes(b"cached second revision")
    return entry
