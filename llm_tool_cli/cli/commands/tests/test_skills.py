import importlib.util
import json
import sys
from enum import StrEnum
from pathlib import Path

import pytest
import typer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from llm_tool_cli.cli.application import create_app
from llm_tool_cli.cli.commands.skills import register_skill_command
from llm_tool_cli.core.settings import ToolLabel, initialize
from llm_tool_cli.core.tests.fixtures import isolated_settings

__all__ = ["isolated_settings"]


class Document(StrEnum):
    overview = "usage"
    custom = "custom-guide"


@pytest.fixture
def skill_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_settings: None) -> typer.Typer:
    initialize(tool_label=ToolLabel("TEST"))
    initializer = tmp_path / "__init__.py"
    initializer.write_text("", encoding="utf-8")
    package = "cli_skill_test_package"
    spec = importlib.util.spec_from_file_location(package, initializer)
    assert spec is not None
    monkeypatch.setitem(sys.modules, package, importlib.util.module_from_spec(spec))
    (tmp_path / "fixtures").mkdir()
    for document in Document:
        (tmp_path / "fixtures" / f"{document.value}.md").write_text(
            f"  # {document.value}\nCafé 日本語\n\n", encoding="utf-8"
        )
    app = create_app(help="Read test documentation.")

    register_skill_command(app, package=package, documents=Document)
    return app


class TestRegisterSkillCommand:
    @pytest.mark.parametrize("document", [None, "usage", "custom-guide"])
    @pytest.mark.parametrize("protocol", [None, "human", "llm", "automation"])
    def test_selected_document_and_protocol(  # noqa: CCR001
        self, skill_app: typer.Typer, tmp_path: Path, protocol: str | None, document: str | None
    ) -> None:
        arguments = [] if protocol is None else ["-p", protocol]
        arguments.extend(["--config", str(tmp_path / "missing.toml"), "skill"])
        if document is not None:
            arguments.append(document)

        result = CliRunner().invoke(skill_app, arguments)

        assert result.exit_code == 0
        assert not result.stderr
        name = document or "usage"
        content = (tmp_path / "fixtures" / f"{name}.md").read_text(encoding="utf-8").strip()
        if protocol == "automation":
            record = json.loads(result.stdout)
            assert record.pop("id")
            assert record == {"type": "skill", "document": name, "content": content}
        else:
            assert result.stdout.startswith("----- TEST CELL " if protocol == "human" else "--TEST-CELL ")
            separator = " = " if protocol == "human" else "="
            assert f"document{separator}{name}\n" in result.stdout
            assert content in result.stdout

    @pytest.mark.parametrize("document", ["missing", "overview", "USAGE", " usage", "../usage", ""])
    def test_unknown_document_fails_before_loading(
        self, skill_app: typer.Typer, mocker: MockerFixture, document: str
    ) -> None:
        loader = mocker.patch("llm_tool_cli.cli.commands.skills.load_skill_text")

        result = CliRunner().invoke(skill_app, ["skill", document])

        assert result.exit_code == 2
        assert not result.stdout
        assert "Invalid value" in result.stderr
        assert "usage" in result.stderr
        assert "custom-guide" in result.stderr
        loader.assert_not_called()

    @pytest.mark.parametrize("protocol", ["human", "llm", "automation"])
    @pytest.mark.parametrize("content", [None, b"\xff"])
    def test_unreadable_document(
        self, skill_app: typer.Typer, tmp_path: Path, protocol: str, content: bytes | None
    ) -> None:
        path = tmp_path / "fixtures" / "usage.md"
        if content is None:
            path.unlink()
        else:
            path.write_bytes(content)

        result = CliRunner().invoke(skill_app, ["-p", protocol, "skill"])

        assert result.exit_code == 3
        if protocol == "automation":
            assert not result.stderr
            record = json.loads(result.stdout)
            assert record["type"] == "error"
            assert record["code"] == "skill_unreadable"
            assert record["document"] == "usage"
            assert record["reason"]
            assert record["content"]
        else:
            assert not result.stdout
            separator = " = " if protocol == "human" else "="
            assert f"code{separator}skill_unreadable\n" in result.stderr
            assert f"document{separator}usage\n" in result.stderr

    def test_empty_document(self, skill_app: typer.Typer, tmp_path: Path) -> None:
        (tmp_path / "fixtures" / "usage.md").write_text("", encoding="utf-8")

        result = CliRunner().invoke(skill_app, ["-p", "automation", "skill"])

        assert result.exit_code == 0
        assert not result.stderr
        assert json.loads(result.stdout)["content"] is None

    def test_unexpected_failure_propagates(self, skill_app: typer.Typer, mocker: MockerFixture) -> None:
        mocker.patch("llm_tool_cli.cli.commands.skills.load_skill_text", side_effect=RuntimeError("broken loader"))

        result = CliRunner().invoke(skill_app, ["skill"])

        assert result.exit_code != 0
        assert isinstance(result.exception, RuntimeError)
        assert not result.stdout
        assert not result.stderr

    def test_help_uses_document_values(self, skill_app: typer.Typer) -> None:
        result = CliRunner().invoke(skill_app, ["skill", "-h"])

        assert result.exit_code == 0
        assert "Print built-in skill documentation." in result.stdout
        assert "usage" in result.stdout
        assert "custom-guide" in result.stdout
        assert "overview" not in result.stdout

    @pytest.mark.parametrize("prefix, expected", [("", ["usage", "custom-guide"]), ("c", ["custom-guide"])])
    def test_completion_uses_document_values(self, skill_app: typer.Typer, prefix: str, expected: list[str]) -> None:
        result = CliRunner().invoke(
            skill_app,
            [],
            prog_name="sample",
            env={"_SAMPLE_COMPLETE": "complete_bash", "COMP_WORDS": f"sample skill {prefix}", "COMP_CWORD": "2"},
        )

        assert result.exit_code == 0
        assert not result.stderr
        assert result.stdout.splitlines() == expected
