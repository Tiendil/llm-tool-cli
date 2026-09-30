import pytest

from llm_tool_cli.cli.entities import GlobalOptions
from llm_tool_cli.protocol import Protocol


class TestGlobalOptions:
    @pytest.mark.parametrize(
        ("command_name", "expected"),
        [
            ("skill", Protocol.llm),
            ("init", Protocol.human),
            ("version", Protocol.human),
            ("custom-command", Protocol.human),
            ("", Protocol.human),
        ],
    )
    def test_protocol_for__command_defaults(self, command_name: str, expected: Protocol) -> None:
        assert GlobalOptions().protocol_for(command_name) == expected

    @pytest.mark.parametrize("protocol", list(Protocol))
    @pytest.mark.parametrize("command_name", ["skill", "init", "custom-command", ""])
    def test_protocol_for__explicit_choice_overrides_defaults(self, protocol: Protocol, command_name: str) -> None:
        assert GlobalOptions(protocol=protocol).protocol_for(command_name) == protocol

    def test_protocol_for__does_not_retain_a_command_default(self) -> None:
        options = GlobalOptions()

        assert options.protocol_for("skill") == Protocol.llm
        assert options.protocol_for("version") == Protocol.human
        assert options.protocol_for("skill") == Protocol.llm
        assert options.protocol is None
