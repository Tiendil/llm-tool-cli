from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from llm_tool_cli.core.entities import ToolName
from llm_tool_cli.paths import ProjectRootPath
from llm_tool_cli.tool_cache import errors as cache_errors
from llm_tool_cli.tool_cache import resolve_cache_root
from llm_tool_cli.tool_state import ToolStateDirectory
from llm_tool_cli.tool_state.project_locks import project_lock_path


class TestResolveCacheRoot:
    def test_override_does_not_move_project_coordination(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.dict("os.environ", {"XDG_STATE_HOME": str(tmp_path / "state")})
        name = ToolName("sample")
        root = ProjectRootPath(tmp_path / "project")
        selected = project_lock_path(ToolStateDirectory.for_tool(name).unwrap(), root).unwrap()
        assert resolve_cache_root(name, Path("elsewhere"), cwd=tmp_path).unwrap() == tmp_path / "elsewhere"
        assert project_lock_path(ToolStateDirectory.for_tool(name).unwrap(), root).unwrap() == selected
        assert not list(tmp_path.iterdir())

    def test_uses_platformdirs_without_creating_directory(self, tmp_path: Path, mocker: MockerFixture) -> None:
        selected = tmp_path / "platform-cache" / "sample"
        discover = mocker.patch("llm_tool_cli.tool_cache.paths.user_cache_path", return_value=selected)
        assert resolve_cache_root(ToolName("sample"), None, cwd=tmp_path).unwrap() == selected
        assert discover.call_args.args == ("sample",)
        assert not selected.exists()

    @pytest.mark.parametrize("discovery", [OSError("unavailable"), RuntimeError("unavailable"), Path("relative")])
    def test_falls_back_to_home_when_discovery_is_unavailable(
        self, tmp_path: Path, mocker: MockerFixture, discovery: Exception | Path
    ) -> None:
        if isinstance(discovery, Exception):
            mocker.patch("llm_tool_cli.tool_cache.paths.user_cache_path", side_effect=discovery)
        else:
            mocker.patch("llm_tool_cli.tool_cache.paths.user_cache_path", return_value=discovery)
        mocker.patch("pathlib.Path.home", return_value=tmp_path)
        assert resolve_cache_root(ToolName("sample"), None, cwd=tmp_path).unwrap() == tmp_path / ".cache" / "sample"
        assert not (tmp_path / ".cache").exists()

    def test_missing_platform_and_home_locations_return_guidance(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("llm_tool_cli.tool_cache.paths.user_cache_path", side_effect=OSError("unavailable"))
        failure = RuntimeError("unavailable")
        mocker.patch("pathlib.Path.home", side_effect=failure)
        problem = resolve_cache_root(ToolName("sample"), None, cwd=tmp_path).unwrap_err()[0]
        assert isinstance(problem, cache_errors.AccessFailed)
        assert problem.reason == str(failure)
        assert problem.ways_to_fix
        assert problem.cause == failure

    def test_relative_override_uses_invocation_directory(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch(
            "llm_tool_cli.tool_cache.paths.user_cache_path", side_effect=AssertionError("unexpected discovery")
        )
        cwd = tmp_path / "tools"
        cwd.mkdir()
        assert resolve_cache_root(ToolName("sample"), Path("../shared"), cwd=cwd).unwrap() == tmp_path / "shared"
        assert not (tmp_path / "shared").exists()

    def test_expands_home_and_resolves_root_alias(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.dict("os.environ", {"HOME": str(tmp_path)})
        original = tmp_path / "original"
        original.mkdir()
        (tmp_path / "alias").symlink_to(original, target_is_directory=True)
        assert (
            resolve_cache_root(ToolName("sample"), Path("~/alias/cache"), cwd=tmp_path).unwrap() == original / "cache"
        )
        assert not (original / "cache").exists()
