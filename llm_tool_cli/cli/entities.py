from llm_tool_cli.core.entities import BaseEntity, ExitCode
from llm_tool_cli.paths import ProjectConfigPath
from llm_tool_cli.protocol import Protocol

__all__ = ["ExitCode", "GlobalOptions"]


class GlobalOptions(BaseEntity):
    """Explicit invocation options, before command defaults or path resolution."""

    protocol: Protocol | None = None
    config_path: ProjectConfigPath | None = None

    def protocol_for(self, command_name: str) -> Protocol:
        """Prefer the explicit protocol; otherwise use LLM for skill and human for other commands."""
        if self.protocol is not None:
            return self.protocol
        return Protocol.llm if command_name == "skill" else Protocol.human
