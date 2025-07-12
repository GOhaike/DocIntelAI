from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Type
from ingramdocai.services.weaviate_client import get_weaviate_client
from ingramdocai.core.logger import setup_logger

logger = setup_logger("fetch_document_chunks")


class FetchDocumentChunksInput(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID for Weaviate multi-tenant isolation")
    user_query: str = Field(..., description="Natural language query string to retrieve document content")


class FetchDocumentChunksTool(BaseTool):
    name: str = "fetch_document_chunks"
    description: str = "Perform semantic search over document chunks for a given tenant using natural language."
    args_schema: Type[BaseModel] = FetchDocumentChunksInput

    def _run(
        self,
        tenant_id: str,
        user_query: str
    ) -> List[Dict[str, Any]]:
        client = None
        try:
            client = get_weaviate_client()
            collection = client.collections.get("DocumentChunk").with_tenant(tenant_id)

            logger.info(f"[{tenant_id}] Query: '{user_query}'")
            results = collection.query.hybrid(query=user_query, limit=5)

            matches = [obj.properties for obj in results.objects or []]
            logger.info(f"[{tenant_id}] Found {len(matches)} match(es)")
            return matches

        except Exception as e:
            logger.exception(f"[{tenant_id}] Document search failed: {e}")
            raise

        finally:
            if client:
                try:
                    client.close()
                    logger.debug(f"[{tenant_id}] Weaviate client closed")
                except Exception as close_err:
                    logger.warning(f"[{tenant_id}] Failed to close Weaviate client: {close_err}")
