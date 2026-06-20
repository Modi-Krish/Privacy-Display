"""
Skills API — CRUD with FAISS re-indexing.
"""
from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.profile import SkillCreate, SkillOut
from app.services.indexing_service import rebuild_index_background

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
async def add_skill(
    body: SkillCreate,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    skill = await db_service.create_skill(current_user.id, body.skill_name, db=db)
    background_tasks.add_task(rebuild_index_background, current_user.id)
    return SkillOut.model_validate(skill)


@router.get("", response_model=list[SkillOut])
async def get_skills(
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    skills = await db_service.get_skills(current_user.id, db=db)
    return [SkillOut.model_validate(s) for s in skills]


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    skill = await db_service.get_skill(skill_id, current_user.id, db=db)
    if not skill:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not found")

    await db_service.delete_skill(skill_id, current_user.id, db=db)
    background_tasks.add_task(rebuild_index_background, current_user.id)
