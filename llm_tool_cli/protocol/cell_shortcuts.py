from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.protocol.logic_cells import ContentCell, EnvironmentErrorCell
from llm_tool_cli.protocol.output_cells.base import MetaValue


def operation_succeeded(message: str, **meta: MetaValue) -> ContentCell:
    return ContentCell(
        kind="operation_succeeded",
        media_type="text/markdown",
        content=message,
        meta={"type": "operation_succeeded", **meta},
    )


def operation_failed(message: str, **meta: MetaValue) -> ContentCell:
    return ContentCell(kind="operation_failed", media_type="text/markdown", content=message, meta=meta)


def info(message: str, **meta: MetaValue) -> ContentCell:
    return ContentCell(kind="info", media_type="text/markdown", content=message, meta=meta)


def skill(document: str, content: str) -> ContentCell:
    return ContentCell(
        kind="skill", media_type="text/markdown", content=content, meta={"type": "skill", "document": document}
    )


def version(value: str) -> ContentCell:
    return ContentCell(kind="version", meta={"type": "version", "version": value})


def environment_error(error: EnvironmentError) -> EnvironmentErrorCell:
    return EnvironmentErrorCell(error=error)
