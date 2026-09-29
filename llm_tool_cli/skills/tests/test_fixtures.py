import importlib.util
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.skills import load_skill_text
from llm_tool_cli.skills.errors import SkillUnreadable


@pytest.fixture
def skill_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    package = "skill_fixture_package"
    initializer = tmp_path / "__init__.py"
    initializer.write_text("", encoding="utf-8")
    spec = importlib.util.spec_from_file_location(package, initializer)
    assert spec is not None
    monkeypatch.setitem(sys.modules, package, importlib.util.module_from_spec(spec))
    (tmp_path / "fixtures").mkdir()
    return package


class TestLoadSkillText:
    @pytest.mark.parametrize(
        ("document", "content"),
        [("usage", "# Usage\n"), ("workflows", ""), ("custom_document", "  Привет 🌍\n\n")],
    )
    def test_reads_selected_utf8_resource(
        self, tmp_path: Path, skill_package: str, document: str, content: str
    ) -> None:
        (tmp_path / "fixtures" / f"{document}.md").write_text(content, encoding="utf-8")

        assert load_skill_text(skill_package, document).unwrap() == content

    @pytest.mark.parametrize("content", [None, b"\xff"])
    def test_read_failure_is_returned(self, tmp_path: Path, skill_package: str, content: bytes | None) -> None:
        if content is not None:
            (tmp_path / "fixtures" / "usage.md").write_bytes(content)

        errors = load_skill_text(skill_package, "usage").unwrap_err()

        assert len(errors) == 1
        failure = errors[0]
        assert isinstance(failure, SkillUnreadable)
        assert failure.code == "skill_unreadable"
        assert failure.document == "usage"
        assert isinstance(failure.cause, FileNotFoundError if content is None else UnicodeDecodeError)
        assert failure.reason == str(failure.cause)
        assert "cause" not in failure.as_record()

    def test_unexpected_failure_propagates(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "llm_tool_cli.skills.fixtures.importlib.resources.files", side_effect=RuntimeError("broken loader")
        )

        with pytest.raises(RuntimeError, match="broken loader"):
            load_skill_text("skill_fixture_package", "usage")
