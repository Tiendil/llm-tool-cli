from __future__ import annotations

import functools
from typing import Callable, Generic, Never, ParamSpec, TypeVar, cast

from llm_tool_cli.core.errors import EnvironmentError, EnvironmentErrors, InternalError

T = TypeVar("T", covariant=True)
U = TypeVar("U")
TValue = TypeVar("TValue")
P = ParamSpec("P")


class UnwrapError(InternalError):
    def __init__(self, error: EnvironmentErrors) -> None:
        super().__init__("Called unwrap on an Err value.", details={"error": error})


class UnwrapErrError(InternalError):
    def __init__(self, value: object) -> None:
        super().__init__("Called unwrap_err on an Ok value.", details={"value": value})


class Result(Generic[T]):
    __slots__ = ("_is_ok", "_value")

    def __init__(self, is_ok: bool, value: T | EnvironmentErrors) -> None:
        self._is_ok = is_ok
        self._value = value

    def is_ok(self) -> bool:
        return self._is_ok

    def is_err(self, error_type: type[EnvironmentError] | None = None) -> bool:
        """Check for failure, optionally requiring all environment errors to match.

        A requested type also matches subclasses. Successes, empty lists, and
        errors outside that type do not match. Without a type, every failed
        result matches, including one with an empty error list.
        """
        if self._is_ok:
            return False
        if error_type is None:
            return True
        errors = cast(EnvironmentErrors, self._value)
        return bool(errors) and all(isinstance(error, error_type) for error in errors)

    def ok(self) -> T | None:
        if self._is_ok:
            return cast(T, self._value)
        return None

    def err(self) -> EnvironmentErrors | None:
        if not self._is_ok:
            return cast(EnvironmentErrors, self._value)
        return None

    def unwrap(self) -> T:
        if self._is_ok:
            return cast(T, self._value)

        raise UnwrapError(error=self.unwrap_err())

    def unwrap_err(self) -> EnvironmentErrors:
        if not self._is_ok:
            return cast(EnvironmentErrors, self._value)

        raise UnwrapErrError(value=self.unwrap())

    def unwrap_or(self, default: U) -> T | U:
        if self._is_ok:
            return cast(T, self._value)
        return default

    def map(self, func: Callable[[T], U]) -> Result[U]:
        if self._is_ok:
            return Result(True, func(cast(T, self._value)))
        return Result(False, cast(EnvironmentErrors, self._value))

    def map_err(self, func: Callable[[EnvironmentErrors], EnvironmentErrors]) -> Result[T]:
        if not self._is_ok:
            return Result(False, func(cast(EnvironmentErrors, self._value)))
        return Result(True, cast(T, self._value))


def Ok(value: TValue) -> Result[TValue]:
    return Result(True, value)


def Err(error: EnvironmentErrors) -> Result[Never]:
    return Result(False, error)


def unwrap_to_error(func: Callable[P, Result[T]]) -> Callable[P, Result[T]]:

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Result[T]:

        try:
            return func(*args, **kwargs)
        except UnwrapError as e:
            return Err(cast(EnvironmentErrors, e.details["error"]))

    return wrapper
