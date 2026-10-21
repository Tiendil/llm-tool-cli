from llm_tool_cli.core import errors as core_errors


class EnvironmentError(core_errors.EnvironmentError):
    """An expected failure while loading a packaged skill document."""


class SkillUnreadable(EnvironmentError):
    code: str = "skill_unreadable"
    message: str = "could not read skill document `{error.document}`: {error.reason}"
    document: str
    reason: str
