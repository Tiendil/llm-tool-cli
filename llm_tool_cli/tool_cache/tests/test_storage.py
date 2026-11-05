import shutil
from pathlib import Path

import pytest
import tomli
from filelock import FileLock, Timeout
from pytest_mock import MockerFixture

from llm_tool_cli.file_locks.tests.helpers import held_lock
from llm_tool_cli.paths import CacheRootPath, PathSegment
from llm_tool_cli.paths import errors as path_errors
from llm_tool_cli.tool_cache import CacheIdentity, ToolCache, errors
from llm_tool_cli.tool_cache.storage import _write_identity
from llm_tool_cli.tool_cache.tests.helpers import cached_entry
from llm_tool_cli.tool_cache.tests.make import cache_storage


class TestWriteIdentity:
    def test_writes_normalized_namespace_and_literal_key(self, tmp_path: Path) -> None:
        identity = CacheIdentity.model_validate({"namespace": " docs ", "key": " key ü\t "})
        marker = tmp_path / "identity.toml"

        _write_identity(marker, identity)

        values = tomli.loads(marker.read_text(encoding="utf-8"))
        assert values == {"namespace": "docs", "key": " key ü\t "}
        assert CacheIdentity.model_validate(values) == identity


class TestToolCache:
    def test_entry__normalizes_directory_and_namespace_names(self, tmp_path: Path) -> None:
        cache = ToolCache(root=CacheRootPath(tmp_path), directory=PathSegment(" entries "), timeout=0)
        identity = CacheIdentity(namespace=PathSegment(" objects "), key="first")

        with cache.entry(identity) as acquired:
            entry = acquired.unwrap()
            assert entry.parent == tmp_path / "entries" / "objects"
            assert tomli.loads((entry / "identity.toml").read_text()) == {"namespace": "objects", "key": "first"}
            assert entry.name == identity.digest
        with cache.entry(CacheIdentity(namespace=PathSegment("objects"), key="first")) as acquired:
            assert acquired.unwrap() == entry
        assert cache.clean().unwrap()
        assert not entry.exists()

    def test_entry__identity_namespace_and_literal_text(self, tmp_path: Path) -> None:
        cache = cache_storage(tmp_path)
        first = CacheIdentity(namespace=PathSegment("objects"), key=" key ü ")
        with cache.entry(first) as acquired:
            entry = acquired.unwrap()
            assert entry.parent == tmp_path / "entries" / "objects"
            assert (entry / "identity.toml").read_text() == 'namespace = "objects"\nkey = " key ü "\n'
        with cache.entry(first) as acquired:
            assert acquired.unwrap() == entry
        for identity in (first.replace(namespace=PathSegment("other")), first.replace(key="key ü")):
            with cache.entry(identity) as acquired:
                assert acquired.unwrap() != entry

    @pytest.mark.parametrize(
        "serialized",
        [
            "# Same identity, different formatting\r\nkey='https://host/shared'\r\nnamespace='objects'\r\n",
            'namespace = " objects "\nkey = "https://host/shared"\n',
        ],
    )
    def test_entry__reuses_and_cleans_equivalent_toml(self, tmp_path: Path, serialized: str) -> None:
        entry = cached_entry(tmp_path)
        marker = entry / "identity.toml"
        marker.write_bytes(serialized.encode("utf-8"))
        cache = cache_storage(tmp_path)

        with cache.entry(CacheIdentity(namespace=PathSegment("objects"), key="https://host/shared")) as acquired:
            assert acquired.unwrap() == entry
            assert marker.read_bytes() == serialized.encode("utf-8")
            assert (entry / "payload" / "versions" / "first").read_bytes() == b"cached first revision"

        assert cache.clean().unwrap()
        assert not entry.exists()

    def test_entry__nested_entries_share_one_lock(self, tmp_path: Path) -> None:
        cache = cache_storage(tmp_path)
        with cache.entry(CacheIdentity(namespace=PathSegment("objects"), key="first")) as outer:
            outer.unwrap()
            with cache.entry(CacheIdentity(namespace=PathSegment("objects"), key="second")) as inner:
                assert inner.unwrap() != outer.unwrap()
            with pytest.raises(Timeout), FileLock(tmp_path / "cache.lock", timeout=0, preserve_lock_file=True):
                pass
        with FileLock(tmp_path / "cache.lock", timeout=0, preserve_lock_file=True):
            pass

    def test_entry__body_failure_releases_lock(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="caller failed"):
            with cache_storage(tmp_path).entry(
                CacheIdentity(namespace=PathSegment("objects"), key="first")
            ) as acquired:
                acquired.unwrap()
                raise ValueError("caller failed")
        with FileLock(tmp_path / "cache.lock", timeout=0, preserve_lock_file=True):
            pass

    @pytest.mark.parametrize("kind", ["different", "malformed", "missing", "symlink", "invalid_utf8"])
    def test_entry__rejects_unowned_existing_data(self, tmp_path: Path, kind: str) -> None:
        entry = cached_entry(tmp_path)
        marker = entry / "identity.toml"
        marker.unlink()
        if kind == "different":
            marker.write_text('namespace = "objects"\nkey = "another"\n')
        elif kind == "malformed":
            marker.write_text("unrelated")
        elif kind == "invalid_utf8":
            marker.write_bytes(b"\xff")
        elif kind == "symlink":
            marker.symlink_to(entry / "payload" / "versions" / "first")
        with cache_storage(tmp_path).entry(
            CacheIdentity(namespace=PathSegment("objects"), key="https://host/shared")
        ) as acquired:
            assert isinstance(acquired.unwrap_err()[0], errors.AccessFailed)
        assert (entry / "payload" / "versions" / "first").read_bytes() == b"cached first revision"

    def test_entry__timeout_preserves_existing_data(self, tmp_path: Path) -> None:
        entry = cached_entry(tmp_path)
        with held_lock(tmp_path / "cache.lock"):
            with cache_storage(tmp_path).entry(
                CacheIdentity(namespace=PathSegment("objects"), key="another")
            ) as acquired:
                problem = acquired.unwrap_err()[0]
                assert isinstance(problem, errors.LockTimeout)
                assert problem.timeout == 0.05
        assert len(list(entry.parent.iterdir())) == 1

    def test_entry__unusable_root_is_preserved(self, tmp_path: Path) -> None:
        root = tmp_path / "cache"
        root.write_text("unrelated")
        with cache_storage(root).entry(CacheIdentity(namespace=PathSegment("objects"), key="first")) as acquired:
            assert isinstance(acquired.unwrap_err()[0], errors.AccessFailed)
        assert root.read_text() == "unrelated"

    def test_entry__native_lock_failure_retains_root_and_cause(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cause = PermissionError("denied")
        mocker.patch("llm_tool_cli.file_locks.files.FileLock", side_effect=cause)
        with cache_storage(tmp_path).entry(CacheIdentity(namespace=PathSegment("objects"), key="first")) as acquired:
            problem = acquired.unwrap_err()[0]
            assert isinstance(problem, errors.AccessFailed)
            assert problem.path == tmp_path
            assert problem.cause == cause

    def test_entry__marker_write_failure_retains_cause_and_releases_lock(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        cause = PermissionError("Marker write denied")
        mocker.patch("llm_tool_cli.tool_cache.storage.tomli_w.dump", side_effect=cause)

        with cache_storage(tmp_path).entry(CacheIdentity(namespace=PathSegment("objects"), key="first")) as acquired:
            problem = acquired.unwrap_err()[0]
            assert isinstance(problem, errors.AccessFailed)
            assert problem.path == tmp_path
            assert problem.cause == cause

        with FileLock(tmp_path / "cache.lock", timeout=0, preserve_lock_file=True):
            pass

    def test_clean__missing_root_does_not_create_directories_or_lock(self, tmp_path: Path) -> None:
        root = CacheRootPath(tmp_path / "absent" / "cache")

        assert not cache_storage(root).clean().unwrap()
        assert not root.parent.exists()

    def test_clean__empty_cache_keeps_the_same_lock_file_on_repeated_cleanup(self, tmp_path: Path) -> None:
        root = CacheRootPath(tmp_path)

        assert not cache_storage(root).clean().unwrap()
        inode = (root / "cache.lock").stat().st_ino
        assert not cache_storage(root).clean().unwrap()
        assert (root / "cache.lock").stat().st_ino == inode
        assert list(root.iterdir()) == [root / "cache.lock"]

    def test_clean__removes_all_owned_entries_and_versions_preserving_unrelated_data(self, tmp_path: Path) -> None:
        root = CacheRootPath(tmp_path / "cache")
        entries = [cached_entry(root, namespace=namespace) for namespace in ("objects", "documents", "results")]
        unrelated = [root / "notes", root / "entries" / "notes", root / "entries" / "objects" / "unmanaged"]
        for path in unrelated:
            path.write_bytes(b"unrelated content")
        inode = (root / "cache.lock").stat().st_ino

        assert cache_storage(root).clean().unwrap()

        assert all(not entry.exists() for entry in entries)
        assert all(path.read_bytes() == b"unrelated content" for path in unrelated)
        assert (root / "cache.lock").stat().st_ino == inode
        assert not cache_storage(root).clean().unwrap()
        with FileLock(root / "cache.lock", timeout=0, preserve_lock_file=True):
            pass

    @pytest.mark.parametrize(
        "marker_state",
        [
            "missing",
            "text",
            "utf8",
            "backend",
            "payload",
            "blank_key",
            "nonstring_namespace",
            "nonstring_key",
            "missing_key",
            "extra_field",
            "duplicate_key",
            "symlink",
            "directory",
        ],
    )
    def test_clean__unverified_ownership_preserves_existing_data(self, tmp_path: Path, marker_state: str) -> None:
        root = CacheRootPath(tmp_path / "cache")
        entry = cached_entry(root)
        marker = entry / "identity.toml"
        original = marker.read_bytes()
        marker.unlink()
        outside = tmp_path / "outside"
        outside.write_bytes(original)
        replacements = {
            "text": b"unrelated data",
            "utf8": b"\xff",
            "backend": b'namespace = "documents"\nkey = "https://host/shared"\n',
            "payload": b'namespace = "objects"\nkey = "https://host/another"\n',
            "blank_key": b'namespace = "objects"\nkey = " "\n',
            "nonstring_namespace": b'namespace = 42\nkey = "https://host/shared"\n',
            "nonstring_key": b'namespace = "objects"\nkey = 42\n',
            "missing_key": b'namespace = "objects"\n',
            "extra_field": b'namespace = "objects"\nkey = "https://host/shared"\nextra = true\n',
            "duplicate_key": b'namespace = "objects"\nkey = "https://host/shared"\nkey = "another"\n',
        }
        if marker_state in replacements:
            marker.write_bytes(replacements[marker_state])
        elif marker_state == "symlink":
            marker.symlink_to(outside)
        elif marker_state == "directory":
            marker.mkdir()

        assert not cache_storage(root).clean().unwrap()

        assert (entry / "payload" / "versions" / "first").read_bytes() == b"cached first revision"
        assert outside.read_bytes() == original
        if marker_state in replacements:
            assert marker.read_bytes() == replacements[marker_state]
        elif marker_state == "symlink":
            assert marker.is_symlink()

    @pytest.mark.parametrize("level", ["entries", "backend", "entry"])
    @pytest.mark.parametrize("kind", ["file", "symlink"])
    def test_clean__unmanaged_cache_layout_is_never_traversed_or_removed(
        self, tmp_path: Path, level: str, kind: str
    ) -> None:
        root = CacheRootPath(tmp_path / "cache")
        outside = tmp_path / "outside"
        cached_entry(outside)
        path = root / {"entries": "entries", "backend": "entries/objects", "entry": "entries/objects/unmanaged"}[level]
        path.parent.mkdir(parents=True)
        if kind == "file":
            path.write_bytes(b"unrelated")
        else:
            path.symlink_to(outside, target_is_directory=True)

        assert not cache_storage(root).clean().unwrap()

        assert path.exists()
        assert any((outside / "entries" / "objects").iterdir())
        if kind == "file":
            assert path.read_bytes() == b"unrelated"
        else:
            assert path.is_symlink()

    def test_clean__payload_symlinks_are_unlinked_without_touching_their_targets(self, tmp_path: Path) -> None:
        root = CacheRootPath(tmp_path / "cache")
        entry = cached_entry(root)
        outside = tmp_path / "source"
        outside.mkdir()
        (outside / "guide").write_bytes(b"source content")
        (entry / "linked-directory").symlink_to(outside, target_is_directory=True)
        (entry / "payload" / "linked-file").symlink_to(outside / "guide")
        (entry / "dangling-link").symlink_to(tmp_path / "absent")

        assert cache_storage(root).clean().unwrap()

        assert not entry.exists()
        assert (outside / "guide").read_bytes() == b"source content"

    def test_clean__cache_lock_blocks_cleanup_and_preserves_cached_data(self, tmp_path: Path) -> None:
        root = CacheRootPath(tmp_path / "cache")
        entry = cached_entry(root)

        with held_lock(root / "cache.lock"):
            problem = cache_storage(root).clean().unwrap_err()[0]

        assert isinstance(problem, errors.LockTimeout)
        assert problem.path == root
        assert (entry / "payload" / "versions" / "first").exists()
        assert cache_storage(root).clean().unwrap()

    def test_clean__cleanup_holds_the_shared_lock_until_deletion_finishes(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        root = CacheRootPath(tmp_path / "cache")
        cached_entry(root)
        remove = shutil.rmtree

        def check_lock(path: Path) -> None:
            with pytest.raises(Timeout):
                FileLock(root / "cache.lock", timeout=0, preserve_lock_file=True).acquire()
            remove(path)

        mocker.patch("llm_tool_cli.tool_cache.storage.shutil.rmtree", side_effect=check_lock)

        assert cache_storage(root).clean().unwrap()

        with FileLock(root / "cache.lock", timeout=0, preserve_lock_file=True):
            pass

    def test_clean__inspection_failure_retains_cause_and_releases_lock(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        root = CacheRootPath(tmp_path / "cache")
        entry = cached_entry(root)
        cause = PermissionError(13, "Unreadable identity", str(entry / "identity.toml"))
        mocker.patch("pathlib.Path.read_text", side_effect=cause)

        problem = cache_storage(root).clean().unwrap_err()[0]

        assert isinstance(problem, errors.AccessFailed)
        assert problem.path == root
        assert problem.cause == cause
        assert (entry / "payload" / "versions" / "first").exists()
        with FileLock(root / "cache.lock", timeout=0, preserve_lock_file=True):
            pass

    def test_clean__failed_deletion_reports_partial_cleanup_and_keeps_ownership_for_retry(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        root = CacheRootPath(tmp_path / "cache")
        entry = cached_entry(root)
        cause = PermissionError(13, "Cannot delete second revision", str(entry / "payload"))

        def fail_after_removing_file(path: Path) -> None:
            (path / "versions" / "first").unlink()
            raise cause

        removal = mocker.patch("llm_tool_cli.tool_cache.storage.shutil.rmtree", side_effect=fail_after_removing_file)

        problem = cache_storage(root).clean().unwrap_err()[0]

        assert isinstance(problem, errors.CleanupFailed)
        assert problem.path == root
        assert problem.entry == entry
        assert problem.cause == cause
        assert "partially" in problem.format_message()
        assert not (entry / "payload" / "versions" / "first").exists()
        assert (entry / "identity.toml").is_file()
        mocker.stop(removal)
        assert cache_storage(root).clean().unwrap()

    def test_clean__regular_file_root_fails_without_removing_it(self, tmp_path: Path) -> None:
        root = CacheRootPath(tmp_path / "cache")
        root.write_bytes(b"unrelated")

        problem = cache_storage(root).clean().unwrap_err()[0]

        assert isinstance(problem, errors.AccessFailed)
        assert problem.path == root
        assert root.read_bytes() == b"unrelated"

    def test_clean__symlinked_lock_is_not_removed_with_disposable_data(self, tmp_path: Path) -> None:
        root = CacheRootPath(tmp_path / "cache")
        entry = cached_entry(root)
        lock_path = root / "cache.lock"
        lock_path.unlink()
        target = entry / "payload" / "versions" / "first"
        lock_path.symlink_to(target)

        problem = cache_storage(root).clean().unwrap_err()[0]

        assert isinstance(problem, path_errors.InvalidProjectPath)
        assert problem.path == str(lock_path)
        assert lock_path.is_symlink()
        assert target.read_bytes() == b"cached first revision"
