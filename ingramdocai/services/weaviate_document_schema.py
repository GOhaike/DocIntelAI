import os
from ingramdocai.core.logger import setup_logger

logger = setup_logger("weaviate_schema")


class WeaviateDocumentSchema:
    """
    Defines the Weaviate schema for vectorized document chunks with multi-tenancy support.
    """

    CLASS_NAME = os.getenv("WEAVIATE_DOC_CLASS", "DocumentChunk")
    DESCRIPTION = "Schema for vectorized chunks from uploaded documents (PDF, DOCX, Excel, etc.)."
    MULTI_TENANCY_CONFIG = {"enabled": True}
    VECTORIZER = os.getenv("WEAVIATE_VECTORIZER", "text2vec-openai")

    PROPERTIES = [
        {"name": "tenant_id", "dataType": ["text"], "description": "Tenant or organization ID"},
        {"name": "session_id", "dataType": ["text"], "description": "Ingestion session ID"},
        {"name": "chunk_id", "dataType": ["text"], "description": "Unique chunk identifier"},
        {"name": "text", "dataType": ["text"], "description": "Chunk content"},
        {"name": "file_name", "dataType": ["text"], "description": "Original document file name"},
        {"name": "file_type", "dataType": ["text"], "description": "File extension (e.g., pdf, docx)"},
        {"name": "char_count", "dataType": ["int"], "description": "Number of characters in chunk"},
        {"name": "source", "dataType": ["text"], "description": "Source loader used"},
        {"name": "page_number", "dataType": ["int"], "description": "Page number (if applicable)"},
        {"name": "created_at", "dataType": ["date"], "description": "Ingestion timestamp"},
    ]

    @classmethod
    def get_schema(cls) -> dict:
        """
        Build and return the full Weaviate class schema.
        """
        schema = {
            "class": cls.CLASS_NAME,
            "description": cls.DESCRIPTION,
            "vectorizer": cls.VECTORIZER,
            "multiTenancyConfig": cls.MULTI_TENANCY_CONFIG,
            "properties": cls.PROPERTIES
        }

        logger.info(
            f"Constructed Weaviate schema '{cls.CLASS_NAME}' "
            f"with {len(cls.PROPERTIES)} properties. Multi-tenancy: {cls.MULTI_TENANCY_CONFIG['enabled']}"
        )
        return schema
