import uuid
import logging
from supabase import create_client, Client
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env to use Supabase Storage")
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client

def upload_file_to_storage(bucket_name: str, file_bytes: bytes, file_name: str, user_id: str | uuid.UUID, content_type: str = "application/pdf") -> str:
    """
    Uploads a file to Supabase Storage and returns the storage path.
    """
    client = get_supabase_client()
    unique_id = uuid.uuid4()
    path = f"{user_id}/{unique_id}_{file_name}"
    
    try:
        client.storage.from_(bucket_name).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        return path
    except Exception as e:
        logger.error(f"Failed to upload file to Supabase Storage: {e}")
        raise e

def get_public_url(bucket_name: str, path: str) -> str:
    """
    Get the public URL for a given storage path.
    """
    client = get_supabase_client()
    return client.storage.from_(bucket_name).get_public_url(path)
