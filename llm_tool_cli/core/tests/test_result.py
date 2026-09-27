import pytest

from llm_tool_cli.core.errors import EnvironmentError, EnvironmentErrors, InternalError
from llm_tool_cli.core.result import Err, Ok, Result, UnwrapErrError, UnwrapError, unwrap_to_error


class ExpectedFailure(EnvironmentError):
    code: str = "expected_failure"
    message: str = "Expected failure"


class SpecificFailure(ExpectedFailure):
    code: str = "specific_failure"


class OtherFailure(EnvironmentError):
    code: str = "other_failure"
    message: str = "Other failure"


class TestResult:
    @pytest.mark.parametrize("errors", [[], [ExpectedFailure()], [ExpectedFailure(), OtherFailure()]])
    def test_is_err__without_type_accepts_any_error_list(self, errors: EnvironmentErrors) -> None:
        result: Result[int] = Err(errors)

        assert result.is_err()
        assert result.is_err(None)
        assert result.unwrap_err() == errors

    @pytest.mark.parametrize("value", [None, 1])
    def test_is_err__success_never_matches(self, value: int | None) -> None:
        result: Result[int | None] = Ok(value)

        assert not result.is_err()
        assert not result.is_err(ExpectedFailure)
        assert result.unwrap() == value

    @pytest.mark.parametrize(
        "errors",
        [[ExpectedFailure()], [SpecificFailure()], [ExpectedFailure(), SpecificFailure()]],
    )
    def test_is_err__matches_all_errors_including_subclasses(self, errors: EnvironmentErrors) -> None:
        result: Result[int] = Err(errors)

        assert result.is_err(ExpectedFailure)
        assert result.unwrap_err() == errors

    @pytest.mark.parametrize(
        "errors",
        [[OtherFailure()], [ExpectedFailure(), OtherFailure()], [OtherFailure(), ExpectedFailure()]],
    )
    def test_is_err__rejects_unmatched_and_mixed_errors(self, errors: EnvironmentErrors) -> None:
        result: Result[int] = Err(errors)

        assert result.is_err()
        assert not result.is_err(ExpectedFailure)
        assert result.unwrap_err() == errors

    def test_is_err__empty_error_list_does_not_match_type(self) -> None:
        result: Result[int] = Err([])

        assert result.is_err()
        assert not result.is_err(ExpectedFailure)

    def test_unwrap__none_is_a_success_value(self) -> None:
        result: Result[None] = Ok(None)

        assert result.is_ok()
        assert result.unwrap() is None

    def test_ok__exposes_success_value(self) -> None:
        result: Result[int] = Ok(2)

        assert result.is_ok()
        assert not result.is_err()
        assert result.ok() == 2
        assert result.err() is None
        assert result.unwrap() == 2
        assert result.unwrap_or(3) == 2

    def test_ok__maps_success_value(self) -> None:
        result: Result[int] = Ok(2)

        mapped = result.map(lambda value: value + 1)
        mapped_error = result.map_err(lambda errors: pytest.fail("must not transform errors on success"))

        assert mapped.unwrap() == 3
        assert mapped_error.unwrap() == 2

    def test_ok__unwrap_err_raises_internal_error(self) -> None:
        result: Result[int] = Ok(2)

        with pytest.raises(UnwrapErrError) as exc_info:
            result.unwrap_err()

        assert exc_info.value.details == {"value": 2}
        assert exc_info.value.message == str(exc_info.value)

    def test_err__exposes_error_value(self) -> None:
        errors: EnvironmentErrors = [ExpectedFailure(), OtherFailure()]
        result: Result[int] = Err(errors)

        assert not result.is_ok()
        assert result.is_err()
        assert result.ok() is None
        assert result.err() == errors
        assert result.unwrap_or(3) == 3

    def test_err__maps_error_value(self) -> None:
        result: Result[int] = Err([ExpectedFailure()])

        mapped = result.map(lambda value: pytest.fail("must not transform a value on failure"))
        mapped_error = result.map_err(lambda errors: [*errors, OtherFailure()])

        assert mapped.err() == [ExpectedFailure()]
        assert mapped_error.err() == [ExpectedFailure(), OtherFailure()]
        assert result.err() == [ExpectedFailure()]

    def test_err__unwrap_raises_internal_error_with_error_value(self) -> None:
        errors: EnvironmentErrors = [ExpectedFailure(), OtherFailure()]
        result: Result[int] = Err(errors)

        with pytest.raises(UnwrapError) as exc_info:
            result.unwrap()

        assert exc_info.value.details == {"error": errors}
        assert exc_info.value.message == str(exc_info.value)


class TestOk:
    def test_returns_success_result(self) -> None:
        assert Ok("value").unwrap() == "value"


class TestErr:
    def test_returns_error_result(self) -> None:
        errors: EnvironmentErrors = [ExpectedFailure(), OtherFailure()]

        assert Err(errors).unwrap_err() == errors


class TestUnwrapToError:
    def test_short_circuits_composition_without_losing_errors(self) -> None:
        calls = []

        @unwrap_to_error
        def composed() -> Result[str]:
            calls.append("before")
            result: Result[str] = Err([ExpectedFailure(), OtherFailure()])
            value = result.unwrap()
            calls.append("after")
            return Ok(value)

        assert composed().unwrap_err() == [ExpectedFailure(), OtherFailure()]
        assert calls == ["before"]

    def test_does_not_hide_unwrap_err_misuse(self) -> None:
        @unwrap_to_error
        def composed() -> Result[str]:
            Ok("value").unwrap_err()
            return Ok("unreachable")

        with pytest.raises(UnwrapErrError):
            composed()

    def test_converts_unwrap_error_to_error_result(self) -> None:
        @unwrap_to_error
        def composed() -> Result[str]:
            return Err([ExpectedFailure()]).unwrap()

        result = composed()

        assert result.is_err()
        assert result.unwrap_err() == [ExpectedFailure()]

    def test_preserves_success_result(self) -> None:
        @unwrap_to_error
        def composed() -> Result[str]:
            return Ok("value")

        assert composed().unwrap() == "value"

    @pytest.mark.parametrize("error", [RuntimeError("boom"), InternalError("technical failure")])
    def test_does_not_hide_arbitrary_exceptions(self, error: Exception) -> None:
        @unwrap_to_error
        def composed() -> Result[str]:
            raise error

        with pytest.raises(type(error)):
            composed()
