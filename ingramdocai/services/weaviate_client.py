import os
from dotenv import load_dotenv
load_dotenv()

import boto3
from weaviate import connect_to_weaviate_cloud, WeaviateClient
from weaviate.classes.init import Auth
from weaviate.exceptions import WeaviateBaseError
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError
from ingramdocai.core.logger import setup_logger

logger = setup_logger("weaviate-client")

# Internal client cache
_client = None


def fetch_ssm_parameters() -> dict:
    """
    Fetch required parameters from AWS SSM Parameter Store.

    Returns:
        dict: A dictionary containing the required parameter values.

    Raises:
        Exception: If any parameter cannot be fetched.
    """
    logger.info("Fetching configuration from AWS SSM Parameter Store...")
    ssm = boto3.client("ssm")
    try:
        params = {
            "WEAVIATE_URL": ssm.get_parameter(Name="/myapp/WEAVIATE_URL", WithDecryption=True)["Parameter"]["Value"],
            "WEAVIATE_API_KEY": ssm.get_parameter(Name="/myapp/WEAVIATE_API_KEY", WithDecryption=True)["Parameter"]["Value"],
            "OPENAI_API_KEY": ssm.get_parameter(Name="/myapp/OPENAI_API_KEY", WithDecryption=True)["Parameter"]["Value"]
        }
        logger.info("Fetched parameters from SSM.")
        return params
    except Exception as e:
        logger.exception(f"Failed to fetch parameters from SSM: {e}")
        raise Exception("SSM Parameter fetch failed") from e


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True
)
def _initialize_weaviate_client(weaviate_url: str, weaviate_api_key: str, openai_api_key: str) -> WeaviateClient:
    """
    Initialize and return a Weaviate client with OpenAI headers.
    Retries with exponential backoff up to 5 times.
    """
    logger.info("Attempting to connect to Weaviate...")
    client = connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key),
        headers={"X-OpenAI-Api-Key": openai_api_key}
    )
    if not client.is_ready():
        logger.warning("Weaviate client initialized but not ready.")
    return client


def get_weaviate_client() -> WeaviateClient:
    """
    Returns a singleton instance of a connected Weaviate client.
    Uses environment variables by default and falls back to AWS SSM Parameter Store
    if required environment variables are missing.
    """
    global _client
    if _client:
        return _client

    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    required_vars = {
        "WEAVIATE_URL": weaviate_url,
        "WEAVIATE_API_KEY": weaviate_api_key,
        "OPENAI_API_KEY": openai_api_key
    }

    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        logger.warning(f"Missing env vars: {', '.join(missing_vars)}. Falling back to SSM...")
        try:
            ssm_params = fetch_ssm_parameters()
            weaviate_url = weaviate_url or ssm_params.get("WEAVIATE_URL")
            weaviate_api_key = weaviate_api_key or ssm_params.get("WEAVIATE_API_KEY")
            openai_api_key = openai_api_key or ssm_params.get("OPENAI_API_KEY")
        except Exception as e:
            logger.error(f"Failed to load required vars from SSM: {e}")
            raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)} and failed to load from SSM.")

    try:
        _client = _initialize_weaviate_client(weaviate_url, weaviate_api_key, openai_api_key)
        logger.info("Connected to Weaviate successfully.")
        return _client

    except RetryError as e:
        logger.error(f"Max retry attempts exceeded. Error: {e}")
        raise

    except WeaviateBaseError as e:
        logger.exception(f"Weaviate client encountered a Weaviate error: {e}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error while initializing Weaviate client: {e}")
        raise


def get_enterprise_weaviate_client(weaviate_url: str, weaviate_api_key: str) -> WeaviateClient:
    """
    Returns a tenant-specific Weaviate client using provided credentials.
    Uses global OpenAI API key.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not weaviate_url or not weaviate_api_key:
        missing = []
        if not weaviate_url:
            missing.append("WEAVIATE_URL")
        if not weaviate_api_key:
            missing.append("WEAVIATE_API_KEY")
        logger.error(f"Missing required parameters for enterprise client: {', '.join(missing)}")
        raise EnvironmentError(f"Missing enterprise Weaviate configuration: {', '.join(missing)}")

    try:
        client = _initialize_weaviate_client(weaviate_url, weaviate_api_key, openai_api_key)
        logger.info("Connected to enterprise Weaviate successfully.")
        return client

    except RetryError as e:
        logger.error(f"Max retry attempts exceeded for enterprise client. Error: {e}")
        raise

    except WeaviateBaseError as e:
        logger.exception(f"Enterprise Weaviate client error: {e}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in enterprise Weaviate connection: {e}")
        raise
