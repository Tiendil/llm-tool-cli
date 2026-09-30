import json
from decimal import Decimal
from pathlib import Path

import pytest

from llm_tool_cli.core.errors import EnvironmentError
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings
from llm_tool_cli.protocol import Protocol
from llm_tool_cli.protocol.logic_cells import EnvironmentErrorCell
from llm_tool_cli.protocol.output_cells import AutomationOutputCell, HumanOutputCell, LLMOutputCell
from llm_tool_cli.protocol.output_cells.base import OutputCell
from llm_tool_cli.protocol.rendering import render_cells

__all__ = ["isolated_settings"]


class ContextFailure(EnvironmentError):
    path: Path
    labels: list[str]
    retryable: bool
    attempts: int
    detail: str | None
    amount: Decimal


class TestEnvironmentErrorCell:
    @pytest.mark.parametrize(
        ("protocol", "output_type"),
        [
            (Protocol.human, HumanOutputCell),
            (Protocol.llm, LLMOutputCell),
            (Protocol.automation, AutomationOutputCell),
        ],
    )
    def test_render__retains_typed_error_and_projects_serialized_context(
        self, protocol: Protocol, output_type: type[OutputCell]
    ) -> None:
        error = ContextFailure(
            code="unavailable",
            message="{error.path}: café\nTry again.",
            path=Path("/project"),
            labels=["one", "two"],
            retryable=False,
            attempts=0,
            detail=None,
            amount=Decimal("1.5"),
        ).with_cause(OSError("private"))
        original = error.model_dump()
        logic_cell = EnvironmentErrorCell(error=error)

        cells = logic_cell.render(protocol)

        assert isinstance(logic_cell.error, ContextFailure)
        assert logic_cell.error.path == Path("/project")
        assert len(cells) == 1
        cell = cells[0]
        assert isinstance(cell, output_type)
        assert cell.kind == "error"
        assert cell.media_type == "text/markdown"
        assert cell.content == "/project: café\nTry again."
        assert cell.meta == {
            "type": "error",
            "code": "unavailable",
            "path": "/project",
            "labels": ["one", "two"],
            "retryable": False,
            "attempts": 0,
            "detail": None,
            "amount": "1.5",
        }
        assert error.model_dump() == original
        assert logic_cell.error.model_dump() == original
        assert isinstance(logic_cell.error.cause, OSError)

    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize(
        ("guidance", "suffix"),
        [
            ([], ""),
            ([" Retry {error.code}. "], "\nWay to fix: Retry unavailable."),
            (
                [" Retry {error.code}. ", "Check configuration."],
                "\n\nWays to fix:\n\n- Retry unavailable.\n- Check configuration.",
            ),
        ],
    )
    def test_render__includes_formatted_guidance(self, protocol: Protocol, guidance: list[str], suffix: str) -> None:
        error = EnvironmentError(code="unavailable", message="Service unavailable", ways_to_fix=guidance)
        original = error.model_dump()

        cell = EnvironmentErrorCell(error=error).render(protocol)[0]

        assert cell.content == "Service unavailable" + suffix
        assert cell.meta == {"type": "error", "code": "unavailable"}
        assert error.model_dump() == original

    @pytest.mark.parametrize("protocol", list(Protocol))
    def test_render__recomputes_output_with_fresh_identifiers(self, protocol: Protocol) -> None:
        error = EnvironmentError(code="empty", message="")
        cell = EnvironmentErrorCell(error=error)

        first = cell.render(protocol)[0]
        second = cell.render(protocol)[0]

        assert first.id != second.id
        assert first.model_dump(exclude={"id"}) == second.model_dump(exclude={"id"})
        assert first.content == ""
        assert first.meta == {"type": "error", "code": "empty"}

    def test_render__preserves_order_and_guidance_in_automation_sequences(self, isolated_settings: None) -> None:
        initialize(tool_label=ToolLabel("TOOL"))
        cells = [
            EnvironmentErrorCell(error=EnvironmentError(code="first", message="First", ways_to_fix=["Retry."])),
            EnvironmentErrorCell(error=EnvironmentError(code="second", message="Second")),
        ]

        output = render_cells(cells, protocol=Protocol.automation)
        records = [json.loads(line) for line in output.splitlines()]

        assert records[0].pop("id") != records[1].pop("id")
        assert records == [
            {"type": "error", "code": "first", "content": "First\nWay to fix: Retry."},
            {"type": "error", "code": "second", "content": "Second"},
        ]
