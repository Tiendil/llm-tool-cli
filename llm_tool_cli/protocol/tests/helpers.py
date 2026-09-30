import base64
import uuid

from llm_tool_cli.core.errors import EnvironmentErrors


def assert_error_cells(records: list[dict[str, object]], errors: EnvironmentErrors) -> None:
    """Assert native automation diagnostics without corrective guidance."""
    assert len(records) == len(errors)
    for record, error in zip(records, errors):
        actual = dict(record)
        cell_id = actual.pop("id")
        assert isinstance(cell_id, str)
        assert uuid.UUID(bytes=base64.urlsafe_b64decode(cell_id + "==")).version == 4
        expected = error.as_record()
        expected["content"] = expected.pop("message")
        assert actual == expected
