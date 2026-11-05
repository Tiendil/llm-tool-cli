import hashlib
import json

import pydantic

from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.paths import PathSegment


class CacheIdentity(BaseEntity):
    """A storage namespace and literal key, independent of cached payloads."""

    model_config = pydantic.ConfigDict(str_strip_whitespace=False)

    namespace: PathSegment
    key: str

    @pydantic.field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        """Keep literal key text; ' key ' is distinct from 'key', while blanks are invalid."""
        if not value.strip():
            raise ValueError("A cache key must not be blank.")
        return value

    @property
    def digest(self) -> str:
        """Hash a canonical namespace/key pair independently of the marker's format."""
        content = json.dumps([self.namespace, self.key], ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
