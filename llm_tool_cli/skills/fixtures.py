import importlib.resources

from llm_tool_cli.core.result import Err, Ok, Result
from llm_tool_cli.skills.errors import SkillUnreadable


def load_skill_text(package: str, document: str) -> Result[str]:
    """Read a selected document from an application-owned package's fixtures."""
    try:
        return Ok(
            importlib.resources.files(package).joinpath("fixtures", f"{document}.md").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError) as error:
        return Err([SkillUnreadable(document=document, reason=str(error)).with_cause(error)])
