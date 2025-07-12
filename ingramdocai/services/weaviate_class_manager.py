import json
from typing import Any, Dict, List
from weaviate.classes.config import Property
from ingramdocai.services.weaviate_client import get_weaviate_client
from ingramdocai.services.weaviate_document_schema import WeaviateDocumentSchema
from ingramdocai.core.logger import setup_logger

logger = setup_logger("weaviate-class-manager")


def list_all_tenants() -> List[str]:
    """Return all tenants registered under the DocumentChunk class."""
    client = get_weaviate_client()
    try:
        col = client.collections.get(WeaviateDocumentSchema.CLASS_NAME)
        tenants = col.tenants.get() or []
        logger.info(f"Tenants for class '{WeaviateDocumentSchema.CLASS_NAME}': {len(tenants)}")
        return tenants
    except Exception as e:
        logger.exception(f"Error listing tenants: {e}")
        return []


def list_classes(tenant_id: str) -> List[str]:
    """Return a list of all class names visible to the tenant."""
    client = get_weaviate_client()
    try:
        classes = client.collections.list_all() or []
        logger.debug(f"[tenant={tenant_id}] Classes: {classes}")
        return classes
    except Exception as e:
        logger.exception(f"[tenant={tenant_id}] Failed to list classes: {e}")
        return []


def delete_class(tenant_id: str, class_name: str) -> None:
    """Delete the specified class if it exists."""
    client = get_weaviate_client()
    try:
        existing = client.collections.list_all() or []
        if class_name not in existing:
            logger.warning(f"[tenant={tenant_id}] Class '{class_name}' not found — skipping delete.")
            return
        client.collections.delete(class_name)
        logger.info(f"[tenant={tenant_id}] Deleted class '{class_name}'.")
    except Exception as e:
        logger.exception(f"[tenant={tenant_id}] Failed to delete class '{class_name}': {e}")


def sync_schema(tenant_id: str) -> None:
    """
    Sync or create the DocumentChunk class schema.
    Adds any missing properties to an existing class.
    """
    client = get_weaviate_client()
    class_name = WeaviateDocumentSchema.CLASS_NAME
    try:
        existing = client.collections.list_all() or []

        if class_name in existing:
            logger.info(f"[tenant={tenant_id}] Syncing properties on existing class '{class_name}'")
            col = client.collections.get(class_name)
            existing_props = {p.name for p in col.config.get().properties}
            for p in WeaviateDocumentSchema.PROPERTIES:
                if p["name"] not in existing_props:
                    new_prop = Property(
                        name=p["name"],
                        data_type=p["dataType"],
                        description=p.get("description")
                    )
                    col.config.add_property(new_prop)
                    logger.info(f"[tenant={tenant_id}] Added property '{p['name']}' to '{class_name}'")
            logger.info(f"[tenant={tenant_id}] Property sync complete for class '{class_name}'")

        else:
            logger.info(f"[tenant={tenant_id}] Creating class '{class_name}'")
            schema_dict = WeaviateDocumentSchema.get_schema()
            client.collections.create_from_dict(schema_dict)
            logger.info(f"[tenant={tenant_id}] Created class '{class_name}'")

    except Exception as e:
        logger.exception(f"[tenant={tenant_id}] Failed to sync schema: {e}")


def ensure_tenant_registered(tenant_id: str) -> bool:
    """
    Ensure the tenant is registered under the DocumentChunk class.
    Returns True if newly created, False if already registered.
    """
    client = get_weaviate_client()
    class_name = WeaviateDocumentSchema.CLASS_NAME
    try:
        if class_name not in client.collections.list_all():
            logger.warning(f"[tenant={tenant_id}] Class '{class_name}' does not exist yet")
            return False

        col = client.collections.get(class_name)
        existing = col.tenants.get() or []
        if tenant_id in existing:
            logger.info(f"[tenant={tenant_id}] Already registered")
            return False

        col.tenants.create(tenant_id)
        logger.info(f"[tenant={tenant_id}] Tenant registered to class '{class_name}'")
        return True

    except Exception as e:
        logger.exception(f"[tenant={tenant_id}] Tenant registration failed: {e}")
        return False


def get_schema_definition() -> Dict[str, Any]:
    """Returns the raw DocumentChunk schema dict for inspection or manual use."""
    schema = WeaviateDocumentSchema.get_schema()
    logger.debug(f"Schema definition: {json.dumps(schema, indent=2)}")
    return schema
