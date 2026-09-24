import pydantic
import pytest

from llm_tool_cli.core.entities import BaseEntity


class _NestedEntity(BaseEntity):
    values: list[int]


class _SampleEntity(BaseEntity):
    name: str
    nested: _NestedEntity


class TestBaseEntity:
    def test_model_config__strips_strings(self) -> None:
        entity = _SampleEntity(name="  value  ", nested=_NestedEntity(values=[]))

        assert entity.name == "value"

    def test_model_config__forbids_extra_fields(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            _SampleEntity.model_validate({"name": "value", "nested": {"values": []}, "extra": True})

    def test_model_config__is_frozen(self) -> None:
        entity = _SampleEntity(name="value", nested=_NestedEntity(values=[]))

        with pytest.raises(pydantic.ValidationError):
            setattr(entity, "name", "changed")

    @pytest.mark.parametrize("changes", [{}, {"name": "after"}])
    def test_replace__returns_deep_copy_with_changes(self, changes: dict[str, object]) -> None:
        entity = _SampleEntity(name="before", nested=_NestedEntity(values=[1]))

        replaced = entity.replace(**changes)
        replaced.nested.values.append(2)

        assert entity.name == "before"
        assert entity.nested.values == [1]
        assert replaced.name == changes.get("name", "before")
        assert replaced.nested.values == [1, 2]

    def test_replace__does_not_normalize_trusted_changes(self) -> None:
        entity = _SampleEntity(name="before", nested=_NestedEntity(values=[]))

        assert entity.replace(name="  after  ").name == "  after  "

    def test_to_json__serializes_entity(self) -> None:
        entity = _SampleEntity(name="value", nested=_NestedEntity(values=[1, 2]))

        assert (
            entity.to_json()
            == '{\n  "name": "value",\n  "nested": {\n    "values": [\n      1,\n      2\n    ]\n  }\n}'
        )

    def test_from_json__deserializes_and_validates_entity(self) -> None:
        entity = _SampleEntity.from_json('{"name": "  value  ", "nested": {"values": [1]}}')

        assert entity == _SampleEntity(name="value", nested=_NestedEntity(values=[1]))

    @pytest.mark.parametrize("json_data", ["{", '{"name": "value", "nested": {"values": ["invalid"]}}'])
    def test_from_json__rejects_invalid_input(self, json_data: str) -> None:
        with pytest.raises(pydantic.ValidationError):
            _SampleEntity.from_json(json_data)
