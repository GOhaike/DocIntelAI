from pydantic import BaseModel, Field
from typing import List, Optional

class DocumentAnalysisOutput(BaseModel):
    classification: str = Field(..., description="Inferred document type (e.g., Contract, Privacy Policy, Report).")
    key_entities: List[str] = Field(..., description="List of extracted entities such as people, organizations, dates, terms, or clauses.")
    critical_clauses: List[str] = Field(..., description="List of key clauses, obligations, requirements, or risks found in the documents.")
    cross_doc_relationships: Optional[str] = Field(None, description="Summary of relationships, contradictions, or dependencies between the analyzed documents.")
    summary: str = Field(..., description="Concise multi-paragraph summary explaining what the documents collectively reveal or imply.")
