import json
from types import MappingProxyType

import pytest

from llm_tool_cli.protocol import Protocol, to_jsonl


class TestToJsonl:
    def test_compact_sorted_unicode_record(self) -> None:
        record = {"z": "日本語", "a": {"z": [True, None, "first\nsecond"], "a": 1}}

        output = to_jsonl(record)

        assert output == '{"a":{"a":1,"z":[true,null,"first\\nsecond"]},"z":"日本語"}\n'
        assert json.loads(output) == record
        assert len(output.splitlines()) == 1

    def test_mapping(self) -> None:
        record = MappingProxyType({"b": 2, "a": 1})

        assert to_jsonl(record) == '{"a":1,"b":2}\n'

    def test_empty_record(self) -> None:
        assert to_jsonl({}) == "{}\n"

    @pytest.mark.parametrize("mode", ["human", "llm", "automation"])
    def test_protocol_wire_value(self, mode: str) -> None:
        assert to_jsonl({"mode": Protocol(mode)}) == f'{{"mode":"{mode}"}}\n'

    def test_unsupported_value(self) -> None:
        with pytest.raises(TypeError):
            to_jsonl({"value": object()})
