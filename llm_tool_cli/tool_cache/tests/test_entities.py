import pydantic
import pytest

from llm_tool_cli.paths import PathSegment
from llm_tool_cli.tool_cache import CacheIdentity


class TestCacheIdentity:
    @pytest.mark.parametrize("namespace", ["", "Objects", "two words", "café", "a_b", "a--b", "a/b"])
    def test_init__rejects_invalid_namespaces(self, namespace: str) -> None:
        with pytest.raises(pydantic.ValidationError):
            CacheIdentity.model_validate({"namespace": namespace, "key": "item"})

    @pytest.mark.parametrize("key", ["", " ", "\t\n"])
    def test_validate_key__rejects_blank_keys(self, key: str) -> None:
        with pytest.raises(pydantic.ValidationError):
            CacheIdentity.model_validate({"namespace": "objects", "key": key})

    def test_validate_key__preserves_literal_identity(self) -> None:
        identity = CacheIdentity.model_validate({"namespace": " docs ", "key": " key ü\t "})
        assert identity.namespace == "docs"
        assert isinstance(identity.namespace, PathSegment)
        assert identity.key == " key ü\t "
        assert identity != CacheIdentity.model_validate({"namespace": " docs ", "key": "key ü"})

    def test_digest__uses_stable_value_encoding(self) -> None:
        identity = CacheIdentity.model_validate({"namespace": "git", "key": "https://host/team/repo"})

        assert identity.digest == "409fdc16ce869345c5e26d235940568ba6692946e7fbee89f201a53f3f561dbc"

    @pytest.mark.parametrize(
        ("namespace", "key"),
        [("ab", "c"), ("a", " bc"), ("a", "bc ")],
    )
    def test_digest__preserves_field_boundaries_and_literal_whitespace(self, namespace: str, key: str) -> None:
        identity = CacheIdentity(namespace=PathSegment("a"), key="bc")

        assert identity.digest != CacheIdentity(namespace=PathSegment(namespace), key=key).digest

    def test_digest__derives_from_both_fields_after_replacement(self) -> None:
        identity = CacheIdentity.model_validate({"namespace": "objects", "key": "first"})
        digest = identity.digest

        for changed in (identity.replace(namespace=PathSegment("documents")), identity.replace(key="second")):
            assert changed.digest != digest
        assert identity.digest == digest
