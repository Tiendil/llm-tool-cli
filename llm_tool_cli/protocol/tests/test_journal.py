import datetime

from llm_tool_cli.protocol.journal import JournalRecord


class TestJournalRecord:
    def test_as_dict__flattens_attributes_and_protects_common_fields(self) -> None:
        timestamp = datetime.datetime.now(datetime.UTC)
        record = JournalRecord(
            message="message",
            timestamp=timestamp,
            attributes={
                "message": "conflict",
                "actor_id": "conflict",
                "timestamp": "conflict",
                "task_id": None,
                "context": {"items": ["first", "second"]},
            },
        )
        original = record.model_dump()
        fields = record.as_dict()
        assert fields == {
            "message": "message",
            "timestamp": timestamp.isoformat(),
            "actor_id": None,
            "task_id": None,
            "context": {"items": ["first", "second"]},
        }
        assert record.model_dump() == original
        assert "attributes" not in fields

    def test_as_dict__returns_independent_nested_data(self) -> None:
        record = JournalRecord(message="event", attributes={"items": ["one"]})
        fields = record.as_dict()
        items = fields["items"]
        assert isinstance(items, list)
        items.append("two")
        assert record.as_dict()["items"] == ["one"]

    def test_timestamp__defaults_to_current_utc_time(self) -> None:
        start = datetime.datetime.now(datetime.UTC)
        record = JournalRecord(message="event")
        assert start <= record.timestamp <= datetime.datetime.now(datetime.UTC)
        assert record.timestamp.utcoffset() == datetime.timedelta(0)
