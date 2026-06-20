import time
from app.core.redis import get_redis_client
from app.core.logging import get_logger

logger = get_logger(__name__)

async def is_rate_limited(key: str, max_attempts: int, window_seconds: int) -> bool:
    """
    Sliding window rate limiter using Redis sorted sets.
    If Redis fails, defaults to False (fails open to avoid service denial for legitimate users, 
    but logs warnings).
    """
    try:
        redis = get_redis_client()
        now = time.time()
        
        pipe = redis.pipeline()
        # Remove timestamps outside the sliding window
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        # Add the current attempt timestamp
        pipe.zadd(key, {str(now): now})
        # Count all elements inside the sliding window
        pipe.zcard(key)
        # Set TTL to ensure the key is cleaned up after the window expires
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        count = results[2]
        
        return count > max_attempts
    except Exception as e:
        logger.warning("Redis rate limiter error, failing open", extra={"error": str(e)})
        return False
