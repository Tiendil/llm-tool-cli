import contextlib
from pathlib import Path

import pydantic
import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.config import (
    create_config,
    errors,
    find_config,
    load_config,
    locate_config,
    read_toml,
    resolve_config_path,
)


class TestFindConfig:
    def test_nearest_file(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        (tmp_path / "config.toml").touch()
        nearest = nested / "config.toml"
        nearest.write_text("not valid TOML", encoding="utf-8")

        assert find_config("config.toml", nested) == nearest

    def test_searches_parents_and_skips_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "config.toml").mkdir()
        outer = tmp_path / "config.toml"
        outer.touch()

        assert find_config("config.toml", nested) == outer

    def test_missing(self, tmp_path: Path) -> None:
        assert find_config(f"{tmp_path.name}-missing.toml", tmp_path) is None

    def test_searches_filesystem_root(self, tmp_path: Path, mocker: MockerFixture) -> None:
        root_config = Path(tmp_path.anchor) / "config.toml"
        mocker.patch.object(Path, "is_file", autospec=True, side_effect=lambda path: path == root_config)

        assert find_config("config.toml", tmp_path) == root_config

    def test_resolves_relative_start(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.touch()

        with contextlib.chdir(tmp_path):
            assert find_config("config.toml", Path(".")) == config_path

    def test_keeps_discovered_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "target.toml"
        target.touch()
        nested = tmp_path / "nested"
        nested.mkdir()
        config_path = nested / "config.toml"
        config_path.symlink_to(target)

        assert find_config("config.toml", nested) == config_path

    def test_resolution_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=OSError("resolution failed"))

        with pytest.raises(errors.DiscoveryFailed) as caught:
            find_config("config.toml", tmp_path)

        assert caught.value.code == "config_discovery_failed"
        assert caught.value.path == tmp_path
        assert isinstance(caught.value.__cause__, OSError)

    def test_inspection_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "is_file", side_effect=PermissionError("access denied"))

        with pytest.raises(errors.DiscoveryFailed) as caught:
            find_config("config.toml", tmp_path)

        assert caught.value.code == "config_discovery_failed"
        assert caught.value.path == tmp_path / "config.toml"
        assert isinstance(caught.value.__cause__, PermissionError)
        assert caught.value.reason == str(caught.value.__cause__)


class TestResolveConfigPath:
    def test_relative_missing_path(self, tmp_path: Path) -> None:
        assert resolve_config_path(Path("nested/../custom.toml"), tmp_path) == tmp_path / "custom.toml"

    def test_absolute_path_ignores_cwd(self, tmp_path: Path) -> None:
        config_path = tmp_path / "custom.toml"

        assert resolve_config_path(config_path, tmp_path / "missing") == config_path

    def test_relative_cwd(self, tmp_path: Path) -> None:
        with contextlib.chdir(tmp_path):
            assert resolve_config_path(Path("custom.toml"), Path("nested")) == tmp_path / "nested/custom.toml"

    def test_follows_symlinks(self, tmp_path: Path) -> None:
        target = tmp_path / "target.toml"
        target.touch()
        link = tmp_path / "custom.toml"
        link.symlink_to(target)

        assert resolve_config_path(link, tmp_path) == target

    def test_expands_home(self, tmp_path: Path, mocker: MockerFixture) -> None:
        home = tmp_path / "home"
        mocker.patch.dict("os.environ", {"HOME": str(home)})

        assert resolve_config_path(Path("~/config.toml"), tmp_path / "cwd") == home / "config.toml"

    def test_preserves_application_syntax(self, tmp_path: Path) -> None:
        assert resolve_config_path(Path("@/config.toml"), tmp_path) == tmp_path / "@/config.toml"

    def test_home_expansion_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = Path("~/config.toml")
        mocker.patch.object(Path, "expanduser", side_effect=RuntimeError("home directory unavailable"))

        with pytest.raises(errors.PathResolutionFailed) as caught:
            resolve_config_path(path, tmp_path)

        assert caught.value.code == "config_path_resolution_failed"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, RuntimeError)
        assert caught.value.reason == str(caught.value.__cause__)

    def test_reported_symlink_loop(self, tmp_path: Path, mocker: MockerFixture) -> None:
        link = tmp_path / "loop"
        mocker.patch.object(Path, "resolve", side_effect=RuntimeError("symlink loop"))

        with pytest.raises(errors.PathResolutionFailed) as caught:
            resolve_config_path(link, tmp_path)

        assert caught.value.code == "config_path_resolution_failed"
        assert caught.value.path == link
        assert isinstance(caught.value.__cause__, (OSError, RuntimeError))

    def test_filesystem_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=PermissionError("access denied"))

        with pytest.raises(errors.PathResolutionFailed) as caught:
            resolve_config_path(Path("custom.toml"), tmp_path)

        assert caught.value.code == "config_path_resolution_failed"
        assert caught.value.path == tmp_path / "custom.toml"
        assert isinstance(caught.value.__cause__, PermissionError)


class TestLocateConfig:
    def test_discovers_nearest_without_reading(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        (tmp_path / "config.toml").touch()
        nearest = nested / "config.toml"
        nearest.write_text("invalid TOML [", encoding="utf-8")

        assert locate_config("config.toml", cwd=nested) == nearest

    def test_discovers_in_parent(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        config_path = tmp_path / "config.toml"
        config_path.touch()

        assert locate_config("config.toml", path=None, cwd=nested) == config_path

    def test_explicit_missing_path_does_not_fall_back(self, tmp_path: Path) -> None:
        (tmp_path / "config.toml").touch()

        assert locate_config("config.toml", path=Path("custom.toml"), cwd=tmp_path) == tmp_path / "custom.toml"

    def test_explicit_home_path(self, tmp_path: Path, mocker: MockerFixture) -> None:
        home = tmp_path / "home"
        mocker.patch.dict("os.environ", {"HOME": str(home)})

        assert locate_config("config.toml", path=Path("~/custom.toml"), cwd=tmp_path) == home / "custom.toml"

    def test_discovered_symlink_keeps_its_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "target.toml"
        target.touch()
        nested = tmp_path / "nested"
        nested.mkdir()
        link = nested / "config.toml"
        link.symlink_to(target)

        assert locate_config("config.toml", cwd=nested) == link

    def test_missing(self, tmp_path: Path) -> None:
        filename = f"{tmp_path.name}-missing.toml"

        with pytest.raises(errors.NotFound) as caught:
            locate_config(filename, cwd=tmp_path)

        assert caught.value.code == "config_not_found"
        assert caught.value.path == tmp_path
        assert filename in caught.value.reason
        assert caught.value.__cause__ is None
        assert caught.value.as_record() == {
            "type": "error",
            "code": "config_not_found",
            "message": caught.value.message,
            "path": str(tmp_path),
            "reason": caught.value.reason,
        }

    def test_discovery_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "is_file", side_effect=PermissionError("access denied"))

        with pytest.raises(errors.DiscoveryFailed) as caught:
            locate_config("config.toml", cwd=tmp_path)

        assert caught.value.path == tmp_path / "config.toml"
        assert isinstance(caught.value.__cause__, PermissionError)

    def test_explicit_resolution_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=PermissionError("access denied"))

        with pytest.raises(errors.PathResolutionFailed) as caught:
            locate_config("config.toml", path=Path("custom.toml"), cwd=tmp_path)

        assert caught.value.path == tmp_path / "custom.toml"
        assert isinstance(caught.value.__cause__, PermissionError)


class TestReadToml:
    def test_toml_1_1_and_utf8(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.write_text('item = {\n label = "café",\n enabled = true,\n}\n', encoding="utf-8")

        assert read_toml(path) == {"item": {"label": "café", "enabled": True}}

    def test_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.touch()

        assert read_toml(path) == {}

    def test_invalid_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.write_text("item = [", encoding="utf-8")

        with pytest.raises(errors.InvalidToml) as caught:
            read_toml(path)

        assert caught.value.code == "config_invalid_toml"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, ValueError)
        assert caught.value.reason == str(caught.value.__cause__)

    def test_invalid_encoding(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.write_bytes(b'label = "\xff"')

        with pytest.raises(errors.InvalidEncoding) as caught:
            read_toml(path)

        assert caught.value.code == "config_invalid_encoding"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, UnicodeDecodeError)

    def test_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"

        with pytest.raises(errors.Unreadable) as caught:
            read_toml(path)

        assert caught.value.code == "config_unreadable"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, FileNotFoundError)
        assert caught.value.as_record() == {
            "type": "error",
            "code": "config_unreadable",
            "message": caught.value.message,
            "path": str(path),
            "reason": str(caught.value.__cause__),
        }

    def test_directory(self, tmp_path: Path) -> None:
        with pytest.raises(errors.Unreadable) as caught:
            read_toml(tmp_path)

        assert caught.value.code == "config_unreadable"
        assert caught.value.path == tmp_path
        assert isinstance(caught.value.__cause__, IsADirectoryError)

    def test_read_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "config.toml"
        path.touch()
        mocker.patch("llm_tool_cli.config.files.tomli.load", side_effect=OSError("read failed"))

        with pytest.raises(errors.Unreadable) as caught:
            read_toml(path)

        assert caught.value.code == "config_unreadable"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, OSError)

    def test_unexpected_parser_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "config.toml"
        path.touch()
        mocker.patch("llm_tool_cli.config.files.tomli.load", side_effect=AssertionError("parser defect"))

        with pytest.raises(AssertionError):
            read_toml(path)


class TestLoadConfig:
    def test_supplied_model(self, tmp_path: Path) -> None:
        class Config(pydantic.BaseModel):
            count: int
            label: str = "default"

        path = tmp_path / "custom.toml"
        path.write_text('count = "3"\n', encoding="utf-8")

        loaded: Config = load_config(path, Config)

        assert loaded == Config(count=3)

    def test_empty_file_uses_model_defaults(self, tmp_path: Path) -> None:
        class Config(pydantic.BaseModel):
            enabled: bool = True

        path = tmp_path / "custom.toml"
        path.touch()

        assert load_config(path, Config) == Config()

    @pytest.mark.parametrize("text", ["", 'count = "invalid"\n', "count = -1\n"])
    def test_validation_failure(self, tmp_path: Path, text: str) -> None:
        class Config(pydantic.BaseModel):
            count: int = pydantic.Field(gt=0)

        path = Path("custom.toml")
        (tmp_path / path).write_text(text, encoding="utf-8")

        with contextlib.chdir(tmp_path), pytest.raises(errors.ValidationFailed) as caught:
            load_config(path, Config)

        assert caught.value.code == "config_validation_failed"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, pydantic.ValidationError)
        assert caught.value.reason == str(caught.value.__cause__)
        assert caught.value.as_record() == {
            "type": "error",
            "code": "config_validation_failed",
            "message": caught.value.message,
            "path": str(path),
            "reason": str(caught.value.__cause__),
        }

    @pytest.mark.parametrize(
        ("data", "expected_error"),
        [(None, errors.Unreadable), (b"item = [", errors.InvalidToml), (b'label = "\xff"', errors.InvalidEncoding)],
    )
    def test_read_failure(self, tmp_path: Path, data: bytes | None, expected_error: type[errors.Error]) -> None:
        path = tmp_path / "custom.toml"
        if data is not None:
            path.write_bytes(data)

        with pytest.raises(expected_error) as caught:
            load_config(path, pydantic.BaseModel)

        assert caught.value.path == path
        assert caught.value.__cause__ is not None

    def test_unexpected_model_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "custom.toml"
        path.touch()
        mocker.patch.object(pydantic.BaseModel, "model_validate", side_effect=TypeError("model defect"))

        with pytest.raises(TypeError):
            load_config(path, pydantic.BaseModel)


class TestCreateConfig:
    @pytest.mark.parametrize("text", ["", '# comment\r\nlabel = "café"\r\n'])
    def test_preserves_text(self, tmp_path: Path, text: str) -> None:
        path = tmp_path / "config.toml"

        create_config(path, text)

        assert path.read_bytes() == text.encode("utf-8")

    def test_refuses_overwrite(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        create_config(path, "original")

        with pytest.raises(errors.AlreadyExists) as caught:
            create_config(path, "replacement")

        assert caught.value.code == "config_already_exists"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, FileExistsError)
        assert path.read_text(encoding="utf-8") == "original"

    def test_existing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(errors.AlreadyExists) as caught:
            create_config(tmp_path, "text")

        assert caught.value.code == "config_already_exists"
        assert caught.value.path == tmp_path
        assert tmp_path.is_dir()

    @pytest.mark.parametrize("target_exists", [False, True])
    def test_existing_symlink(self, tmp_path: Path, target_exists: bool) -> None:
        target = tmp_path / "target.toml"
        if target_exists:
            target.write_text("original", encoding="utf-8")
        path = tmp_path / "config.toml"
        path.symlink_to(target)

        with pytest.raises(errors.AlreadyExists) as caught:
            create_config(path, "replacement")

        assert caught.value.code == "config_already_exists"
        assert path.is_symlink()
        if target_exists:
            assert target.read_text(encoding="utf-8") == "original"
        else:
            assert not target.exists()

    def test_missing_parent(self, tmp_path: Path) -> None:
        path = tmp_path / "missing/config.toml"

        with pytest.raises(errors.Unwritable) as caught:
            create_config(path, "text")

        assert caught.value.code == "config_unwritable"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, FileNotFoundError)
        assert not path.parent.exists()

    def test_invalid_text(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"

        with pytest.raises(errors.Unwritable) as caught:
            create_config(path, "\ud800")

        assert caught.value.code == "config_unwritable"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, UnicodeEncodeError)
        assert not path.exists()

    def test_write_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "config.toml"
        stream = mocker.patch.object(Path, "open").return_value.__enter__.return_value
        stream.write.side_effect = OSError("write failed")

        with pytest.raises(errors.Unwritable) as caught:
            create_config(path, "text")

        assert caught.value.code == "config_unwritable"
        assert caught.value.path == path
        assert isinstance(caught.value.__cause__, OSError)
