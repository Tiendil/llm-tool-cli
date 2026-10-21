"""Independent typed bindings with initialization and temporary scopes."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from llm_tool_cli.core.errors import ContextValueAlreadySet, ContextValueNotSet


class ContextValue[T]:
    """Access one value in the current execution context.

    The name is diagnostic only. Each instance owns an independent binding;
    binding an object does not copy it or manage its resources.
    """

    __slots__ = ("_variable",)

    def __init__(self, name: str) -> None:
        self._variable: ContextVar[T] = ContextVar(name)

    def get(self) -> T:
        """Return the bound value, raising an internal exception when unset."""
        try:
            return self._variable.get()
        except LookupError as error:
            raise ContextValueNotSet(details={"name": self._variable.name}) from error

    def is_set(self) -> bool:
        """Report whether a value is bound, including an explicit None."""
        try:
            self._variable.get()
        except LookupError:
            return False
        return True

    def initialize(self, value: T) -> None:
        """Install a value once in the current context, rejecting reassignment."""
        if self.is_set():
            raise ContextValueAlreadySet(details={"name": self._variable.name})
        self._variable.set(value)

    @contextmanager
    def scope(self, value: T) -> Iterator[None]:
        """Temporarily bind a value and restore the previous binding on exit."""
        token = self._variable.set(value)
        try:
            yield
        finally:
            self._variable.reset(token)
