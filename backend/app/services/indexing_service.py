import json
import logging
from uuid import UUID
from app.core.redis import get_cache
from app.tasks.tasks import rebuild_rag_index_task

logger = logging.getLogger(__name__)

# Keep a dummy/empty indexing_progress for backward compatibility if needed, but not used.
indexing_progress = {}

def rebuild_index_background(user_id: UUID) -> None:
    """Dispatches the index rebuild task to Celery."""
    rebuild_rag_index_task.delay(str(user_id))

async def get_progress(user_id: UUID) -> dict:
    """Fetches the indexing progress from Redis."""
    try:
        data = await get_cache(f"indexing_progress:{user_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to read indexing progress from Redis: {e}")
    return {"status": "idle"}

