from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.auth import ProfileUpdate, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("", response_model=ProfileOut)
async def get_profile(
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    profile = await db_service.get_profile(current_user.id, db=db)
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return ProfileOut.model_validate(profile)

@router.put("", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    profile = await db_service.create_or_update_profile(
        current_user.id,
        full_name=body.full_name,
        summary=body.summary,
        db=db
    )
    return ProfileOut.model_validate(profile)
