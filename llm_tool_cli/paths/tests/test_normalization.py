from pathlib import Path

import pytest

from llm_tool_cli.paths import is_project_path_id, normalize_project_path_id
from llm_tool_cli.paths.errors import InvalidProjectPath


class TestIsProjectPathId:
    @pytest.mark.parametrize(
        "value",
        [
            "@/README.md",
            "@/README",
            "@/LICENSE",
            "@/Makefile",
            "@/assets",
            "@/assets/archive",
            "@/src/package",
            "@/notes/Проектный план",
            "@/notes/project plan.md",
            "@/Case/FILE",
            "@/ directory / file ",
            "@/a/.../b",
            "@/~/file",
            "@/a\\b/file",
            "@/name:section",
            "@/src/{**package_path}/*.[pP][yY]",
        ],
    )
    def test_accepts_canonical_project_paths(self, value: str) -> None:
        assert is_project_path_id(value)

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "@",
            "@file",
            "file",
            "./file",
            "/project/file",
            " @/file",
            "@/",
            "@/.",
            "@/..",
            "@//file",
            "@/a//b",
            "@/a/",
            "@/a/..",
            "@/../a",
            "@/a/../../a",
        ],
    )
    def test_rejects_malformed_project_paths(self, value: str) -> None:
        assert not is_project_path_id(value)

    @pytest.mark.parametrize("value", ["@/./a", "@/a/.", "@/a/../b", "@/a/b/.."])
    def test_rejects_paths_requiring_normalization(self, value: str) -> None:
        assert not is_project_path_id(value)

    @pytest.mark.parametrize("value", [None, 1, b"@/file", [], {}, Path("@/file")])
    def test_rejects_non_strings(self, value: object) -> None:
        assert not is_project_path_id(value)


class TestNormalizeProjectPathId:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("@/file", "@/file"),
            ("@/a/./b/../c", "@/a/c"),
            ("@/./a", "@/a"),
            ("@/a/.", "@/a"),
            ("@/a/b/..", "@/a"),
            ("@/a/../b", "@/b"),
            ("@/a/b/../../c", "@/c"),
        ],
    )
    def test_normalization(self, value: str, expected: str) -> None:
        normalized = normalize_project_path_id(value).unwrap()

        assert normalized == expected
        assert normalize_project_path_id(normalized).unwrap() == normalized

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "@",
            "@file",
            "file",
            "./file",
            "/file",
            " @/file",
            "@/",
            "@/.",
            "@/..",
            "@//file",
            "@/a//b",
            "@/a/",
            "@/a/..",
            "@/a/../.",
            "@/../a",
            "@/a/../../a",
        ],
    )
    def test_invalid_path(self, value: str) -> None:
        errors = normalize_project_path_id(value).unwrap_err()

        assert len(errors) == 1
        error = errors[0]
        assert isinstance(error, InvalidProjectPath)
        assert error.code == "invalid_project_path"
        assert error.path == value.strip()

    @pytest.mark.parametrize(
        "value",
        [
            "@/Case/FILE",
            "@/café/資料",
            "@/ directory / file ",
            "@/a/.../b",
            "@/~/file",
            "@/a\\b/file",
            "@/name:section",
            "@/src/{**package_path}/*.[pP][yY]",
        ],
    )
    def test_preserves_segment_text(self, value: str) -> None:
        assert normalize_project_path_id(value).unwrap() == value

    def test_structured_error(self) -> None:
        error = normalize_project_path_id("@/../file").unwrap_err()[0]

        assert error.as_record() == {
            "type": "error",
            "code": "invalid_project_path",
            "message": error.format_message(),
            "path": "@/../file",
        }
