from typing import List, Dict, Any
from weaviate.exceptions import WeaviateBaseError
from ingramdocai.services.weaviate_client import get_weaviate_client
from ingramdocai.services.weaviate_document_schema import WeaviateDocumentSchema
from ingramdocai.services.weaviate_class_manager import sync_schema, ensure_tenant_registered
from ingramdocai.core.logger import setup_logger

logger = setup_logger("document-chunk-upsert")


def bulk_upsert_document_chunks(items: List[Dict[str, Any]]) -> None:
    """
    Bulk insert document chunks into Weaviate for a single tenant.

    - Each item must include a valid 'tenant_id'.
    - All items must belong to the same tenant.
    - The function ensures the schema is synced and tenant is registered.
    - Items are inserted in fixed-size batches (100 per batch).
    - Embeddings should already be stored in the item via vector store ingestion logic.

    Parameters:
    - items: List of chunk dictionaries, one per document segment.

    Raises:
    - ValueError: If tenant_id is missing or inconsistent.
    - Exception: If Weaviate write fails.
    """
    if not items:
        logger.warning("No document chunks to upsert.")
        return

    tenant_id = items[0].get("tenant_id", "").strip().lower()
    if not tenant_id:
        raise ValueError("Missing 'tenant_id' in the first document chunk.")

    for i, item in enumerate(items):
        item_tenant = item.get("tenant_id", "").strip().lower()
        if item_tenant != tenant_id:
            raise ValueError(f"All chunks must belong to the same tenant. Mismatch at index {i}.")

    try:
        client = get_weaviate_client()
        class_name = WeaviateDocumentSchema.CLASS_NAME

        # Ensure schema and tenant are initialized
        sync_schema(tenant_id)
        if ensure_tenant_registered(tenant_id):
            logger.info(f"[tenant={tenant_id}] Tenant was newly registered.")
        else:
            logger.info(f"[tenant={tenant_id}] Tenant already exists.")

        # Scope the collection to the tenant
        collection = client.collections.get(class_name)
        tenant_collection = collection.with_tenant(tenant_id)

        # Batch insert
        with tenant_collection.batch.fixed_size(batch_size=100) as batch:
            for item in items:
                item["tenant_id"] = tenant_id  
                batch.add_object(item)

        failed = tenant_collection.batch.failed_objects or []
        success = len(items) - len(failed)

        logger.info(f"[tenant={tenant_id}] Upsert complete: {success}/{len(items)} document chunks.")
        if failed:
            logger.warning(f"[tenant={tenant_id}] Failed objects: {failed}")

    except Exception as e:
        logger.exception(f"[tenant={tenant_id}] Bulk upsert of document chunks failed.")
        raise
