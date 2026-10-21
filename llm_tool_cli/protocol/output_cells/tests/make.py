import uuid

from llm_tool_cli.protocol.output_cells.base import OutputCell


def cell(cell_type: type[OutputCell], **kwargs: object) -> OutputCell:
    values = {
        "id": uuid.UUID("12345678-1234-5678-9234-567812345678"),
        "kind": "sample_status",
        "media_type": "text/markdown",
        "content": "  Sample content.  ",
        "meta": {"zeta": 2, "alpha": "first", "enabled": True, "missing": None},
    }
    values.update(kwargs)
    return cell_type.model_validate(values)
