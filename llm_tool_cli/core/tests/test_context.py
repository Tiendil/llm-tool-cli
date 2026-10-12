from contextvars import Context

import pytest

from llm_tool_cli.core.context import ContextValue
from llm_tool_cli.core.errors import ContextValueAlreadySet, ContextValueNotSet


class TestContextValue:
    def test_get__missing_value_identifies_binding(self) -> None:
        value = ContextValue[str]("workspace")

        with pytest.raises(ContextValueNotSet) as caught:
            value.get()

        assert caught.value.details == {"name": "workspace"}
        assert not value.is_set()

    @pytest.mark.parametrize("initial", [None, False, 0, "", "  café 日本語  ", []])
    def test_initialize__preserves_value_in_current_context(self, initial: object) -> None:
        value = ContextValue[object]("setting")
        execution = Context()

        execution.run(value.initialize, initial)

        assert execution.run(value.is_set)
        assert execution.run(value.get) == initial
        assert not value.is_set()

    @pytest.mark.parametrize(
        ("initial", "replacement"),
        [("first", "second"), ("first", "first"), (None, None), (None, "second")],
    )
    def test_initialize__rejects_reassignment_and_preserves_value(
        self, initial: str | None, replacement: str | None
    ) -> None:
        value = ContextValue[str | None]("setting")
        execution = Context()
        execution.run(value.initialize, initial)

        with pytest.raises(ContextValueAlreadySet) as caught:
            execution.run(value.initialize, replacement)

        assert caught.value.details == {"name": "setting"}
        assert execution.run(value.get) == initial

    def test_initialize__rejects_assignment_during_scope(self) -> None:
        value = ContextValue[str]("setting")

        with value.scope("temporary"):
            with pytest.raises(ContextValueAlreadySet):
                value.initialize("replacement")

            assert value.get() == "temporary"

        execution = Context()
        execution.run(value.initialize, "permanent")
        assert execution.run(value.get) == "permanent"

    def test_scope__binds_on_entry_and_restores_unset_state(self) -> None:
        value = ContextValue[str]("setting")
        scope = value.scope("temporary")
        assert not value.is_set()

        with scope:
            assert value.is_set()
            assert value.get() == "temporary"

        assert not value.is_set()
        with pytest.raises(ContextValueNotSet):
            value.get()

    def test_scope__restores_initialized_value(self) -> None:
        value = ContextValue[str]("setting")
        execution = Context()
        execution.run(value.initialize, "initial")

        def override() -> None:
            with value.scope("temporary"):
                assert value.get() == "temporary"

            assert value.get() == "initial"

        execution.run(override)
        assert not value.is_set()

    @pytest.mark.parametrize("outer", [None, "outer"])
    def test_scope__nested_scopes_restore_previous_values(self, outer: str | None) -> None:
        value = ContextValue[str | None]("operation")

        with value.scope(outer):
            with value.scope("middle"):
                with value.scope(None):
                    assert value.is_set()
                    assert value.get() is None

                assert value.get() == "middle"

            assert value.is_set()
            assert value.get() == outer

        assert not value.is_set()

    @pytest.mark.parametrize("error", [ValueError("failure"), SystemExit(1)])
    def test_scope__restores_previous_value_after_exception(self, error: BaseException) -> None:
        value = ContextValue[str]("setting")

        with value.scope("outer"):
            with pytest.raises(type(error)) as caught:
                with value.scope("inner"):
                    raise error

            assert caught.value == error
            assert value.get() == "outer"

        assert not value.is_set()

    def test_scope__restores_unset_state_after_exception(self) -> None:
        value = ContextValue[str]("setting")

        with pytest.raises(ValueError):
            with value.scope("temporary"):
                raise ValueError("failure")

        assert not value.is_set()
        with pytest.raises(ContextValueNotSet):
            value.get()

    def test_scope__same_name_does_not_share_bindings(self) -> None:
        first = ContextValue[str]("setting")
        second = ContextValue[str]("setting")

        with first.scope("first"):
            assert not second.is_set()
            with second.scope("second"):
                assert first.get() == "first"
                assert second.get() == "second"

            assert first.get() == "first"
            assert not second.is_set()

        assert not first.is_set()

    def test_scope__preserves_object_mutations(self) -> None:
        value = ContextValue[list[str]]("cache")
        original: list[str] = []

        with value.scope(original):
            value.get().append("loaded")
            assert original == ["loaded"]

        assert original == ["loaded"]
