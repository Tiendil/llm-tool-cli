from pathlib import Path
from types import MappingProxyType

import pytest

from llm_tool_cli.core.errors import EnvironmentError, EnvironmentErrors, EnvironmentErrorsProxy, InternalError


class TestInternalError:
    @pytest.mark.parametrize("message", [None, "", "operation failed"])
    def test_init__message_fallback(self, message: str | None) -> None:
        error = InternalError(message)
        expected = "InternalError" if message is None else message

        assert error.message == expected
        assert str(error) == expected
        assert error.args == (expected,)

    @pytest.mark.parametrize("details", [None, {}])
    def test_init__empty_details_are_independent(self, details: dict[str, object] | None) -> None:
        first = InternalError(details=details)
        second = InternalError(details=details)
        first.details["path"] = "config.toml"

        assert not second.details
        if details is not None:
            assert not details

    def test_init__copies_mapping(self) -> None:
        details: dict[str, object] = {"path": "original.toml"}
        error = InternalError(details=MappingProxyType(details))
        details["path"] = "changed.toml"
        details["extra"] = True

        assert error.details == {"path": "original.toml"}

    def test_init__nested_values_remain_shared(self) -> None:
        items = ["original"]
        error = InternalError(details={"items": items})
        items.append("added")

        assert error.details["items"] == ["original", "added"]

    def test_message__uses_exception_arguments(self) -> None:
        error = InternalError("original")
        error.args = ("updated",)

        assert error.message == str(error) == "updated"


class ResourceUnavailable(EnvironmentError):
    code: str = "resource_unavailable"
    message: str = "Resource {error.path}: {error.reason}"
    path: Path
    reason: str


class TestEnvironmentError:
    def test_format_message__substitutes_typed_context(self) -> None:
        error = ResourceUnavailable(path=Path("resource.txt"), reason="access denied")

        assert error.format_message() == "Resource resource.txt: access denied"

    def test_format_message__uses_normalized_context(self) -> None:
        error = ResourceUnavailable(
            path=Path("resource.txt"),
            message="  Resource {error.path}: {error.reason}\n",
            reason="  café\n  {literal}\n",
        )

        assert error.format_message() == "Resource resource.txt: café\n  {literal}"

    def test_as_record__serializes_context_without_template_fields(self) -> None:
        error = ResourceUnavailable(
            path=Path("resource.txt"), reason="access denied", ways_to_fix=["Check {error.path}"]
        )

        assert error.as_record() == {
            "type": "error",
            "code": "resource_unavailable",
            "message": "Resource resource.txt: access denied",
            "path": "resource.txt",
            "reason": "access denied",
        }

    def test_with_cause__keeps_debugging_context_private(self) -> None:
        cause = PermissionError("access denied")
        error = ResourceUnavailable(path=Path("resource.txt"), reason=str(cause))
        original_record = error.as_record()

        returned = error.with_cause(cause)

        assert returned == error
        assert error.cause == cause
        assert error.as_record() == original_record
        assert "cause" not in error.model_dump_json()

    def test_cause__without_original_exception(self) -> None:
        error = ResourceUnavailable(path=Path("resource.txt"), reason="not configured")

        assert error.cause is None


class TestEnvironmentErrorsProxy:
    @pytest.mark.parametrize("reasons", [[], ["unavailable", "access denied"]])
    def test_init__retains_original_error_list(self, reasons: list[str]) -> None:
        errors: EnvironmentErrors = [
            ResourceUnavailable(path=Path("resource.txt"), reason=reason) for reason in reasons
        ]

        proxy = EnvironmentErrorsProxy(errors)

        assert proxy.details == {"errors": errors}

        errors.append(ResourceUnavailable(path=Path("other.txt"), reason="missing"))

        assert proxy.details == {"errors": errors}
