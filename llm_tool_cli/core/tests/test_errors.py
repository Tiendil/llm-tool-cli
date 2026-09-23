from types import MappingProxyType

import pytest

from llm_tool_cli.core.errors import Error


class ExampleFailure(Error):
    code = "example_failure"


class TestError:
    @pytest.mark.parametrize("message", [None, "", "operation failed"])
    def test_init__message_fallback(self, message: str | None) -> None:
        error = ExampleFailure(message)
        expected = "ExampleFailure" if message is None else message

        assert error.message == expected
        assert str(error) == expected
        assert error.args == (expected,)

    def test_init__code_override_is_local(self) -> None:
        error = ExampleFailure("operation failed", code="specific_failure")

        assert error.as_record()["code"] == "specific_failure"
        assert ExampleFailure().as_record()["code"] == "example_failure"

    @pytest.mark.parametrize("details", [None, {}])
    def test_init__empty_details_are_independent(self, details: dict[str, object] | None) -> None:
        first = Error(details=details)
        second = Error(details=details)
        first.details["path"] = "config.toml"

        assert not second.details
        if details is not None:
            assert not details

    def test_init__copies_mapping(self) -> None:
        details: dict[str, object] = {"path": "original.toml"}
        error = Error(details=MappingProxyType(details))
        details["path"] = "changed.toml"
        details["extra"] = True

        assert error.details == {"path": "original.toml"}

    def test_init__nested_values_remain_shared(self) -> None:
        items = ["original"]
        error = Error(details={"items": items})
        items.append("added")

        assert error.details["items"] == ["original", "added"]

    def test_message__uses_exception_arguments(self) -> None:
        error = Error("original")
        error.args = ("updated",)

        assert error.message == str(error) == "updated"

    def test_as_record__includes_context(self) -> None:
        error = ExampleFailure("operation failed", details={"path": "config.toml"})

        assert error.as_record() == {
            "path": "config.toml",
            "type": "error",
            "code": "example_failure",
            "message": "operation failed",
        }

    def test_as_record__protects_reserved_fields(self) -> None:
        details: dict[str, object] = {"type": "other", "code": "other", "message": "other"}
        error = ExampleFailure("operation failed", details=details)

        assert error.as_record() == {
            "type": "error",
            "code": "example_failure",
            "message": "operation failed",
        }
        assert error.details == details

    def test_as_record__returns_new_mapping(self) -> None:
        error = Error("operation failed", details={"path": "original.toml"})
        record = error.as_record()
        record["path"] = "changed.toml"
        record["message"] = "changed message"

        assert error.as_record()["path"] == "original.toml"
        assert error.message == "operation failed"
