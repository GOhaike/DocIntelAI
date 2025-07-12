from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from ingramdocai.persistence.db import Base

class DocumentSession(Base):
    __tablename__ = "document_sessions"

    session_id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

