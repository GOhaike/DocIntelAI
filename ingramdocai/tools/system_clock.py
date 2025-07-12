# tools/system_time.py

from crewai.tools import BaseTool
from pydantic import BaseModel
from typing import Any, Type
from datetime import datetime, timezone

class EmptyArgs(BaseModel):
    pass

class GetCurrentUTCTimeTool(BaseTool):
    """
    Tool: GetCurrentUTCTimeTool
    -----------------------------------
    Returns the current UTC timestamp in ISO format.
    Used by agents to compare the current system time against job update timestamps
    when calculating how recent a job update occurred.

    This is useful in status agents for document injection, allowing them to report
    how long ago the job was updated (e.g., "2 minutes ago").

    Output Format: "YYYY-MM-DD HH:MM:SS" (UTC timezone)
    """

    name: str = "get_current_time"
    description: str = (
        "Returns the current UTC time in the format 'YYYY-MM-DD HH:MM:SS'. "
        "Use this to calculate how long ago a document injection job was last updated."
    )
    args_schema: Type[BaseModel] = EmptyArgs

    def _run(self, **kwargs: Any) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
