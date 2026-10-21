from pathlib import Path
from typing import Annotated, Literal

import pydantic
import pytest

from llm_tool_cli.config import errors, load_config
from llm_tool_cli.config.fields import ConfigVersion, SessionDir, validate_relative_project_path
from llm_tool_cli.core.entities import BaseEntity
from llm_tool_cli.paths import RelativeProjectPath


class ExampleConfig(BaseEntity):
    version: ConfigVersion[Literal[1]] = 1
    session_dir: SessionDir = RelativeProjectPath(Path(".session/example"))


class TestValidateConfigVersion:
    def test_accepts_supported_integer(self) -> None:
        assert pydantic.TypeAdapter(ConfigVersion[Literal[1]]).validate_python(1) == 1

    def test_uses_application_version_constraint(self) -> None:
        adapter: pydantic.TypeAdapter[int] = pydantic.TypeAdapter(ConfigVersion[Literal[2]])

        assert adapter.validate_python(2) == 2
        with pytest.raises(pydantic.ValidationError) as failure:
            adapter.validate_python(1)

        assert "Unsupported configuration version 1" in failure.value.errors()[0]["msg"]
        assert "supported version: 2" in failure.value.errors()[0]["msg"]

    def test_preserves_other_schema_failures(self) -> None:
        adapter: pydantic.TypeAdapter[int] = pydantic.TypeAdapter(ConfigVersion[Annotated[int, pydantic.Field(gt=0)]])

        with pytest.raises(pydantic.ValidationError) as failure:
            adapter.validate_python(0)

        assert failure.value.errors()[0]["type"] == "greater_than"

    @pytest.mark.parametrize("value", [True, False, 1.0, "1", "", None, []])
    def test_rejects_wrong_types_before_conversion(self, value: object) -> None:
        with pytest.raises(pydantic.ValidationError) as failure:
            pydantic.TypeAdapter(ConfigVersion[Literal[1]]).validate_python(value)

        detail = failure.value.errors()[0]
        assert detail["type"] == "value_error"
        assert "integer" in detail["msg"]
        assert repr(value) in detail["msg"]

    @pytest.mark.parametrize("value", [-1, 0, 2])
    def test_reports_unsupported_version_and_supported_version(self, value: int) -> None:
        with pytest.raises(pydantic.ValidationError) as failure:
            pydantic.TypeAdapter(ConfigVersion[Literal[1]]).validate_python(value)

        detail = failure.value.errors()[0]
        assert detail["type"] == "value_error"
        assert "Unsupported configuration version" in detail["msg"]
        assert str(value) in detail["msg"]
        assert "supported version: 1" in detail["msg"]


class TestValidateRelativeProjectPath:
    @pytest.mark.parametrize("value", [".", "workflows", ".session/example", "~/literal"])
    def test_accepts_relative_paths_without_resolution(self, value: str) -> None:
        path = RelativeProjectPath(Path(value))

        assert validate_relative_project_path(path) == path

    @pytest.mark.parametrize("value", ["/outside", "..", "../outside", "nested/../outside"])
    def test_rejects_absolute_paths_and_parent_references(self, value: str) -> None:
        with pytest.raises(ValueError):
            validate_relative_project_path(RelativeProjectPath(Path(value)))


class TestConfigurationFields:
    @pytest.mark.parametrize("text", ["", "version = 2\n"])
    def test_load_config__tool_can_select_another_version_and_default(self, tmp_path: Path, text: str) -> None:
        class VersionTwoConfig(BaseEntity):
            version: ConfigVersion[Literal[2]] = 2

        path = tmp_path / "config.toml"
        path.write_text(text, encoding="utf-8")

        config = load_config(path, VersionTwoConfig).unwrap()

        assert config.version == 2
        assert VersionTwoConfig.from_json(config.to_json()) == config

    @pytest.mark.parametrize("version_line", ["", "version = 1\n"])
    def test_load_config__relative_directory_round_trip_without_creating_storage(
        self, tmp_path: Path, version_line: str
    ) -> None:
        path = tmp_path / "config.toml"
        path.write_text(version_line + 'session_dir = "./custom/./state"\n', encoding="utf-8")

        config = load_config(path, ExampleConfig).unwrap()

        assert config.model_dump(mode="json") == {"version": 1, "session_dir": "custom/state"}
        assert ExampleConfig.from_json(config.to_json()) == config
        assert not (tmp_path / "custom").exists()

    @pytest.mark.parametrize(
        ("text", "field"),
        [
            ("version = 2", "version"),
            ('version = "1"', "version"),
            ("version = true", "version"),
            ("version = 1.0", "version"),
            ('session_dir = "/outside"', "session_dir"),
            ('session_dir = "nested/../outside"', "session_dir"),
        ],
    )
    def test_load_config__invalid_fields_use_shared_diagnostic(self, tmp_path: Path, text: str, field: str) -> None:
        path = tmp_path / "config.toml"
        path.write_text(text, encoding="utf-8")

        failure = load_config(path, ExampleConfig).unwrap_err()[0]

        assert isinstance(failure, errors.ValidationFailed)
        assert failure.path == path
        assert isinstance(failure.cause, pydantic.ValidationError)
        detail = failure.cause.errors()[0]
        assert detail["loc"] == (field,)
        assert detail["msg"] in failure.reason
