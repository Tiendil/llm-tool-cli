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

        assert find_config("config.toml", nested).unwrap() == nearest

    def test_searches_parents_and_skips_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "config.toml").mkdir()
        outer = tmp_path / "config.toml"
        outer.touch()

        assert find_config("config.toml", nested).unwrap() == outer

    def test_missing(self, tmp_path: Path) -> None:
        assert find_config(f"{tmp_path.name}-missing.toml", tmp_path).unwrap() is None

    def test_searches_filesystem_root(self, tmp_path: Path, mocker: MockerFixture) -> None:
        root_config = Path(tmp_path.anchor) / "config.toml"
        mocker.patch.object(Path, "is_file", autospec=True, side_effect=lambda path: path == root_config)

        assert find_config("config.toml", tmp_path).unwrap() == root_config

    def test_resolves_relative_start(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.toml"
        config_path.touch()

        with contextlib.chdir(tmp_path):
            assert find_config("config.toml", Path(".")).unwrap() == config_path

    def test_keeps_discovered_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "target.toml"
        target.touch()
        nested = tmp_path / "nested"
        nested.mkdir()
        config_path = nested / "config.toml"
        config_path.symlink_to(target)

        assert find_config("config.toml", nested).unwrap() == config_path

    def test_resolution_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=OSError("resolution failed"))

        caught = find_config("config.toml", tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.DiscoveryFailed)

        assert caught.code == "config_discovery_failed"
        assert caught.path == tmp_path
        assert isinstance(caught.cause, OSError)

    def test_inspection_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "is_file", side_effect=PermissionError("access denied"))

        caught = find_config("config.toml", tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.DiscoveryFailed)

        assert caught.code == "config_discovery_failed"
        assert caught.path == tmp_path / "config.toml"
        assert isinstance(caught.cause, PermissionError)
        assert caught.reason == str(caught.cause)


class TestResolveConfigPath:
    def test_relative_missing_path(self, tmp_path: Path) -> None:
        assert resolve_config_path(Path("nested/../custom.toml"), tmp_path).unwrap() == tmp_path / "custom.toml"

    def test_absolute_path_ignores_cwd(self, tmp_path: Path) -> None:
        config_path = tmp_path / "custom.toml"

        assert resolve_config_path(config_path, tmp_path / "missing").unwrap() == config_path

    def test_relative_cwd(self, tmp_path: Path) -> None:
        with contextlib.chdir(tmp_path):
            assert resolve_config_path(Path("custom.toml"), Path("nested")).unwrap() == tmp_path / "nested/custom.toml"

    def test_follows_symlinks(self, tmp_path: Path) -> None:
        target = tmp_path / "target.toml"
        target.touch()
        link = tmp_path / "custom.toml"
        link.symlink_to(target)

        assert resolve_config_path(link, tmp_path).unwrap() == target

    def test_expands_home(self, tmp_path: Path, mocker: MockerFixture) -> None:
        home = tmp_path / "home"
        mocker.patch.dict("os.environ", {"HOME": str(home)})

        assert resolve_config_path(Path("~/config.toml"), tmp_path / "cwd").unwrap() == home / "config.toml"

    def test_preserves_application_syntax(self, tmp_path: Path) -> None:
        assert resolve_config_path(Path("@/config.toml"), tmp_path).unwrap() == tmp_path / "@/config.toml"

    def test_home_expansion_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = Path("~/config.toml")
        mocker.patch.object(Path, "expanduser", side_effect=RuntimeError("home directory unavailable"))

        caught = resolve_config_path(path, tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.PathResolutionFailed)

        assert caught.code == "config_path_resolution_failed"
        assert caught.path == path
        assert isinstance(caught.cause, RuntimeError)
        assert caught.reason == str(caught.cause)

    def test_reported_symlink_loop(self, tmp_path: Path, mocker: MockerFixture) -> None:
        link = tmp_path / "loop"
        mocker.patch.object(Path, "resolve", side_effect=RuntimeError("symlink loop"))

        caught = resolve_config_path(link, tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.PathResolutionFailed)

        assert caught.code == "config_path_resolution_failed"
        assert caught.path == link
        assert isinstance(caught.cause, (OSError, RuntimeError))

    def test_filesystem_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=PermissionError("access denied"))

        caught = resolve_config_path(Path("custom.toml"), tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.PathResolutionFailed)

        assert caught.code == "config_path_resolution_failed"
        assert caught.path == tmp_path / "custom.toml"
        assert isinstance(caught.cause, PermissionError)


class TestLocateConfig:
    def test_discovers_nearest_without_reading(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        (tmp_path / "config.toml").touch()
        nearest = nested / "config.toml"
        nearest.write_text("invalid TOML [", encoding="utf-8")

        assert locate_config("config.toml", cwd=nested).unwrap() == nearest

    def test_discovers_in_parent(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        config_path = tmp_path / "config.toml"
        config_path.touch()

        assert locate_config("config.toml", path=None, cwd=nested).unwrap() == config_path

    def test_explicit_missing_path_does_not_fall_back(self, tmp_path: Path) -> None:
        (tmp_path / "config.toml").touch()

        assert (
            locate_config("config.toml", path=Path("custom.toml"), cwd=tmp_path).unwrap() == tmp_path / "custom.toml"
        )

    def test_explicit_home_path(self, tmp_path: Path, mocker: MockerFixture) -> None:
        home = tmp_path / "home"
        mocker.patch.dict("os.environ", {"HOME": str(home)})

        assert locate_config("config.toml", path=Path("~/custom.toml"), cwd=tmp_path).unwrap() == home / "custom.toml"

    def test_discovered_symlink_keeps_its_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "target.toml"
        target.touch()
        nested = tmp_path / "nested"
        nested.mkdir()
        link = nested / "config.toml"
        link.symlink_to(target)

        assert locate_config("config.toml", cwd=nested).unwrap() == link

    def test_missing(self, tmp_path: Path) -> None:
        filename = f"{tmp_path.name}-missing.toml"

        caught = locate_config(filename, cwd=tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.NotFound)

        assert caught.code == "config_not_found"
        assert caught.path == tmp_path
        assert filename in caught.reason
        assert caught.cause is None
        assert caught.as_record() == {
            "type": "error",
            "code": "config_not_found",
            "message": caught.format_message(),
            "path": str(tmp_path),
            "reason": caught.reason,
        }

    def test_discovery_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "is_file", side_effect=PermissionError("access denied"))

        caught = locate_config("config.toml", cwd=tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.DiscoveryFailed)

        assert caught.path == tmp_path / "config.toml"
        assert isinstance(caught.cause, PermissionError)

    def test_explicit_resolution_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(Path, "resolve", side_effect=PermissionError("access denied"))

        caught = locate_config("config.toml", path=Path("custom.toml"), cwd=tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.PathResolutionFailed)

        assert caught.path == tmp_path / "custom.toml"
        assert isinstance(caught.cause, PermissionError)


class TestReadToml:
    def test_toml_1_1_and_utf8(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.write_text('item = {\n label = "café",\n enabled = true,\n}\n', encoding="utf-8")

        assert read_toml(path).unwrap() == {"item": {"label": "café", "enabled": True}}

    def test_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.touch()

        assert read_toml(path).unwrap() == {}

    def test_invalid_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.write_text("item = [", encoding="utf-8")

        caught = read_toml(path).unwrap_err()[0]
        assert isinstance(caught, errors.InvalidToml)

        assert caught.code == "config_invalid_toml"
        assert caught.path == path
        assert isinstance(caught.cause, ValueError)
        assert caught.reason == str(caught.cause)

    def test_invalid_encoding(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        path.write_bytes(b'label = "\xff"')

        caught = read_toml(path).unwrap_err()[0]
        assert isinstance(caught, errors.InvalidEncoding)

        assert caught.code == "config_invalid_encoding"
        assert caught.path == path
        assert isinstance(caught.cause, UnicodeDecodeError)

    def test_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"

        caught = read_toml(path).unwrap_err()[0]
        assert isinstance(caught, errors.Unreadable)

        assert caught.code == "config_unreadable"
        assert caught.path == path
        assert isinstance(caught.cause, FileNotFoundError)
        assert caught.as_record() == {
            "type": "error",
            "code": "config_unreadable",
            "message": caught.format_message(),
            "path": str(path),
            "reason": str(caught.cause),
        }

    def test_directory(self, tmp_path: Path) -> None:
        caught = read_toml(tmp_path).unwrap_err()[0]
        assert isinstance(caught, errors.Unreadable)

        assert caught.code == "config_unreadable"
        assert caught.path == tmp_path
        assert isinstance(caught.cause, IsADirectoryError)

    def test_read_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "config.toml"
        path.touch()
        mocker.patch("llm_tool_cli.config.files.tomli.load", side_effect=OSError("read failed"))

        caught = read_toml(path).unwrap_err()[0]
        assert isinstance(caught, errors.Unreadable)

        assert caught.code == "config_unreadable"
        assert caught.path == path
        assert isinstance(caught.cause, OSError)

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

        loaded: Config = load_config(path, Config).unwrap()

        assert loaded == Config(count=3)

    def test_empty_file_uses_model_defaults(self, tmp_path: Path) -> None:
        class Config(pydantic.BaseModel):
            enabled: bool = True

        path = tmp_path / "custom.toml"
        path.touch()

        assert load_config(path, Config).unwrap() == Config()

    @pytest.mark.parametrize("text", ["", 'count = "invalid"\n', "count = -1\n"])
    def test_validation_failure(self, tmp_path: Path, text: str) -> None:
        class Config(pydantic.BaseModel):
            count: int = pydantic.Field(gt=0)

        path = Path("custom.toml")
        (tmp_path / path).write_text(text, encoding="utf-8")

        with contextlib.chdir(tmp_path):
            caught = load_config(path, Config).unwrap_err()[0]

        assert isinstance(caught, errors.ValidationFailed)

        assert caught.code == "config_validation_failed"
        assert caught.path == path
        assert isinstance(caught.cause, pydantic.ValidationError)
        assert caught.reason == str(caught.cause)
        assert caught.as_record() == {
            "type": "error",
            "code": "config_validation_failed",
            "message": caught.format_message(),
            "path": str(path),
            "reason": str(caught.cause),
        }

    @pytest.mark.parametrize(
        ("data", "expected_error"),
        [(None, errors.Unreadable), (b"item = [", errors.InvalidToml), (b'label = "\xff"', errors.InvalidEncoding)],
    )
    def test_read_failure(
        self, tmp_path: Path, data: bytes | None, expected_error: type[errors.EnvironmentError]
    ) -> None:
        path = tmp_path / "custom.toml"
        if data is not None:
            path.write_bytes(data)

        caught = load_config(path, pydantic.BaseModel).unwrap_err()[0]
        assert isinstance(caught, expected_error)

        assert caught.path == path
        assert caught.cause is not None

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

        assert create_config(path, text).unwrap() is None

        assert path.read_bytes() == text.encode("utf-8")

    def test_refuses_overwrite(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"
        create_config(path, "original").unwrap()

        caught = create_config(path, "replacement").unwrap_err()[0]
        assert isinstance(caught, errors.AlreadyExists)

        assert caught.code == "config_already_exists"
        assert caught.path == path
        assert isinstance(caught.cause, FileExistsError)
        assert path.read_text(encoding="utf-8") == "original"

    def test_existing_directory(self, tmp_path: Path) -> None:
        caught = create_config(tmp_path, "text").unwrap_err()[0]
        assert isinstance(caught, errors.AlreadyExists)

        assert caught.code == "config_already_exists"
        assert caught.path == tmp_path
        assert tmp_path.is_dir()

    @pytest.mark.parametrize("target_exists", [False, True])
    def test_existing_symlink(self, tmp_path: Path, target_exists: bool) -> None:
        target = tmp_path / "target.toml"
        if target_exists:
            target.write_text("original", encoding="utf-8")
        path = tmp_path / "config.toml"
        path.symlink_to(target)

        caught = create_config(path, "replacement").unwrap_err()[0]
        assert isinstance(caught, errors.AlreadyExists)

        assert caught.code == "config_already_exists"
        assert path.is_symlink()
        if target_exists:
            assert target.read_text(encoding="utf-8") == "original"
        else:
            assert not target.exists()

    def test_missing_parent(self, tmp_path: Path) -> None:
        path = tmp_path / "missing/config.toml"

        caught = create_config(path, "text").unwrap_err()[0]
        assert isinstance(caught, errors.Unwritable)

        assert caught.code == "config_unwritable"
        assert caught.path == path
        assert isinstance(caught.cause, FileNotFoundError)
        assert not path.parent.exists()

    def test_invalid_text(self, tmp_path: Path) -> None:
        path = tmp_path / "config.toml"

        caught = create_config(path, "\ud800").unwrap_err()[0]
        assert isinstance(caught, errors.Unwritable)

        assert caught.code == "config_unwritable"
        assert caught.path == path
        assert isinstance(caught.cause, UnicodeEncodeError)
        assert not path.exists()

    def test_write_failure(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "config.toml"
        stream = mocker.patch.object(Path, "open").return_value.__enter__.return_value
        stream.write.side_effect = OSError("write failed")

        caught = create_config(path, "text").unwrap_err()[0]
        assert isinstance(caught, errors.Unwritable)

        assert caught.code == "config_unwritable"
        assert caught.path == path
        assert isinstance(caught.cause, OSError)
