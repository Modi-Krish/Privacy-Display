import redis.asyncio as aioredis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis_client = None

def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client

async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

async def ping_redis() -> bool:
    try:
        client = get_redis_client()
        return await client.ping()
    except Exception as e:
        logger.error("Redis ping failed", extra={"error": str(e)})
        return False

async def get_cache(key: str) -> str | None:
    try:
        client = get_redis_client()
        return await client.get(key)
    except Exception as e:
        logger.error(f"Redis get failed for key {key}", extra={"error": str(e)})
        return None

async def set_cache(key: str, val: str, ttl: int = 3600) -> None:
    try:
        client = get_redis_client()
        await client.set(key, val, ex=ttl)
    except Exception as e:
        logger.error(f"Redis set failed for key {key}", extra={"error": str(e)})

async def delete_cache(key: str) -> None:
    try:
        client = get_redis_client()
        await client.delete(key)
    except Exception as e:
        logger.error(f"Redis delete failed for key {key}", extra={"error": str(e)})

