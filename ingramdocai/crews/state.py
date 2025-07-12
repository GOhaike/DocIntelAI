from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid


class IngramDocAIFlowState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique run ID for the current execution.")

    # Flat input fields
    user_id: str = Field(default="", description="User ID that initiated the task.")
    tenant_id: str = Field(default="", description="Tenant or organization identifier.")
    session_id: str = Field(default="", description="Session identifier used for document lifecycle tracking.")
    task_type: str = Field(default="", description="Type of user task: inject, query, analyze, or status.")
    user_query: Optional[str] = Field(default="", description="Natural language query provided by the user.")
    task_payload: Dict[str, Any] = Field(default_factory=dict, description="Flat task payload, if present.")
    user_info: Dict[str, Any] = Field(default_factory=dict, description="Resolved user metadata with session context.")

    # Outputs
    chunk_count: Optional[int] = Field(default=None, description="Number of chunks created during document injection.")
    query_answer: Optional[Dict[str, Any]] = Field(default=None, description="Final answer from document query agent.")
    status_summary: Optional[Dict[str, Any]] = Field(default=None, description="Job status result based on session_id.")
    document_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Full output from document analysis crew.")
    debug_metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional field for tracking debug or runtime values.")
