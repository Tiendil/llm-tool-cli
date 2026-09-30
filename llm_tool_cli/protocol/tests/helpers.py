import base64
import uuid

from llm_tool_cli.core.errors import EnvironmentErrors


def cell_payloads(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Validate generated cell IDs and return payload copies without them."""
    payloads = []
    for record in records:
        payload = dict(record)
        cell_id = payload.pop("id")
        assert isinstance(cell_id, str)
        assert uuid.UUID(bytes=base64.urlsafe_b64decode(cell_id + "==")).version == 4
        payloads.append(payload)
    return payloads


def assert_error_cells(records: list[dict[str, object]], errors: EnvironmentErrors) -> None:
    """Assert native automation diagnostics without corrective guidance."""
    assert len(records) == len(errors)
    for actual, error in zip(cell_payloads(records), errors):
        expected = error.as_record()
        expected["content"] = expected.pop("message")
        assert actual == expected
