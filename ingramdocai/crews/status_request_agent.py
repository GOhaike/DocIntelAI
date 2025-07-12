# agents/status_query_agent.py

from crewai.agent import Agent
from pydantic import BaseModel, Field
from typing import List
from ingramdocai.tools.status import FetchUserJobStatusTool
from ingramdocai.tools.system_clock import GetCurrentUTCTimeTool


class StatusQueryState(BaseModel):
    job_status_summary: str = Field(
        ..., description="Summary of the current document processing job status."
    )


status_query_agent = Agent(
    role="IngramDocAI Status Agent",
    goal="Tell the user the current document status using official tools only.",
    backstory=(
        "You are the official status checker for IngramDocAI. "
        "Your job is to return the current document processing status. "
        "You must always use the `fetch_user_job_status` tool to get status information for the session, "
        "and only use `get_current_time` to calculate how recently each record was updated. "
        "Do not guess or make up results."
    ),
    tools=[
        FetchUserJobStatusTool(),
        GetCurrentUTCTimeTool()
    ],
    allow_delegation=False,
    verbose=False
)

# --------------------------------------------------
# Instruction Template
# --------------------------------------------------

def status_query_instruction(session_id: str) -> str:
    return f"""
Check the current document processing status using the tools provided.

Steps:
1. Call `fetch_user_job_status` with the session_id: `{session_id}`
2. If no records are found, say:
   "We couldn’t find any document processing session matching your request."
3. If records are found:
   - Call `get_current_time` to get the current UTC time
   - For each record:
     - Show its status (e.g., completed, in_progress, failed)
     - Include chunk count if available
     - Include error message if available
     - Mention how long ago it was updated

Return your answer as one clear paragraph under the key `job_status_summary`.

Do not return raw records. Do not guess. Only report what the tools return.
"""
