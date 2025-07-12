
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Any, Type, List, Dict
from ingramdocai.services.database import get_db_session
from ingramdocai.persistence.models import DocumentSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import OperationalError


class FetchUserJobStatusArgs(BaseModel):
    session_id: str = Field(..., description="Session ID used during document injection.")


class FetchUserJobStatusTool(BaseTool):
    name: str = "fetch_user_job_status"
    description: str = (
        "Fetches all document injection jobs matching a given session_id from the local DB. "
        "Returns full record details for inspection."
    )
    args_schema: Type[BaseModel] = FetchUserJobStatusArgs

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=4),
        retry=retry_if_exception_type(OperationalError)
    )
    def _run(self, session_id: str) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            records = (
                session.query(DocumentSession)
                .filter_by(session_id=session_id)
                .order_by(DocumentSession.updated_at.desc())
                .all()
            )

            return [
                {
                    k: (v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v)
                    for k, v in r.__dict__.items()
                    if k != "_sa_instance_state"
                }
                for r in records
            ]
