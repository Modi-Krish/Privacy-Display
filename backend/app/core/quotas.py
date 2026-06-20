import datetime
import logging
from uuid import UUID
from fastapi import HTTPException, status
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# Daily limits
MAX_AI_RESPONSES_PER_DAY = 100
MAX_UPLOADS_PER_DAY = 50

async def check_quota(user_id: UUID, op: str, limit: int) -> None:
    """
    Checks if a user has exceeded their daily quota for a specific operation.
    Increments the daily counter in Redis.
    """
    try:
        r = get_redis_client()
        date_str = datetime.date.today().isoformat()
        key = f"quota:{op}:{user_id}:{date_str}"
        
        count = await r.incr(key)
        if count == 1:
            # Set 24 hour expiry on creation
            await r.expire(key, 86400)
            
        if count > limit:
            logger.warning(
                "User quota exceeded",
                extra={"user_id": str(user_id), "op": op, "count": count, "limit": limit}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily quota exceeded for {op} (max {limit}/day)."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Quota check failed, passing through",
            extra={"user_id": str(user_id), "op": op, "error": str(e)}
        )
        # Fallback: fail open so Redis issues don't block user actions
        return

async def check_upload_quota(user_id: UUID) -> None:
    await check_quota(user_id, "uploads", MAX_UPLOADS_PER_DAY)

async def check_ai_quota(user_id: UUID) -> None:
    await check_quota(user_id, "ai_calls", MAX_AI_RESPONSES_PER_DAY)
