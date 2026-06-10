"""
Skills API — CRUD with FAISS re-indexing.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, Skill
from app.schemas.profile import SkillCreate, SkillOut
from app.api.projects import _rebuild_index  # shared rebuild helper

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
async def add_skill(
    body: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skill = Skill(user_id=current_user.id, skill_name=body.skill_name)
    db.add(skill)
    await db.flush()
    await _rebuild_index(current_user.id, db)
    return SkillOut.model_validate(skill)


@router.get("", response_model=list[SkillOut])
async def get_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Skill).where(Skill.user_id == current_user.id))
    return [SkillOut.model_validate(s) for s in result.scalars().all()]


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.user_id == current_user.id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not found")

    await db.delete(skill)
    await db.flush()
    await _rebuild_index(current_user.id, db)
