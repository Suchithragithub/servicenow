import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

def get_openai_client():
    return AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION")
    )

OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT")

def get_embedding_client():
    """
    Returns a separate Azure OpenAI client configured for the embedding
    deployment (text-embedding-3-large), using its own endpoint/key/version.
    """
    endpoint = os.getenv("AZURE_OPENAI_EMBED_API_ENDPOINT", "").strip().strip('"')
 
    # The endpoint in your .env includes the full path + query string.
    # AzureOpenAI client only needs the base resource URL, e.g.:
    #   https://azure-openai-uk.openai.azure.com
    # So we extract just the base part.
    base_endpoint = endpoint.split("/openai/deployments")[0]
 
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_EMBED_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_EMBED_VERSION", "2023-05-15"),
        azure_endpoint=base_endpoint,
    )
 
 
EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_MODEL", "text-embedding-3-large")