from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type
from datetime import datetime
from ingramdocai.core.logger import setup_logger
from ingramdocai.persistence.db import SessionLocal
from ingramdocai.persistence.models import DocumentSession
from sqlalchemy.exc import SQLAlchemyError

logger = setup_logger("save_session_record")


class SaveSessionInput(BaseModel):
    session_id: str = Field(..., description="Session ID for this ingestion run")
    tenant_id: str = Field(..., description="Tenant ID for the organization")
    user_id: str = Field(..., description="User ID who initiated the ingestion")
    file_path: Optional[str] = Field(None, description="Absolute path to the document")
    status: Optional[str] = Field(None, description="Status: in_progress, completed, failed")
    chunk_count: Optional[int] = Field(None, description="Number of chunks")
    error_message: Optional[str] = Field(None, description="Failure message (if any)")
    created_at: Optional[datetime] = Field(None, description="Start time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class SaveSessionRecordTool(BaseTool):
    name: str = "save_session_record"
    description: str = (
        "Insert or update a document ingestion session record in the database. "
        "If file_path is provided, creates a new record. Otherwise, updates an existing one."
    )
    args_schema: Type[BaseModel] = SaveSessionInput

    def _run(
        self,
        session_id: str,
        tenant_id: str,
        user_id: str,
        file_path: Optional[str] = None,
        status: Optional[str] = None,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> str:
        db = SessionLocal()

        try:
            record = db.query(DocumentSession).filter_by(session_id=session_id).first()

            if record:
                # Update logic
                if status:
                    record.status = status
                if chunk_count is not None:
                    record.chunk_count = chunk_count
                if error_message:
                    record.error_message = error_message
                record.updated_at = updated_at or datetime.utcnow()
                db.commit()
                logger.info(f"Session {session_id} updated → status={status}")
                return "updated"

            else:
                # Insert logic
                if not file_path:
                    raise ValueError("file_path is required to create a new session.")
                new_record = DocumentSession(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    file_path=file_path,
                    status=status or "in_progress",
                    chunk_count=chunk_count or 0,
                    error_message=error_message,
                    created_at=created_at or datetime.utcnow(),
                    updated_at=updated_at or datetime.utcnow()
                )
                db.add(new_record)
                db.commit()
                logger.info(f"Session {session_id} created")
                return "inserted"

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error in SaveSessionRecordTool: {str(e)}")
            raise

        finally:
            db.close()
            logger.info("Database session closed in SaveSessionRecordTool")