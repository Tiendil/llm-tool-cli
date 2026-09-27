import json
from collections.abc import Mapping


def to_jsonl(record: Mapping[str, object]) -> str:
    """Serialize a record as one compact, Unicode-preserving JSON line."""
    return json.dumps(dict(record), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
