"""
Projects API — CRUD with FAISS re-embedding on create/update.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, Project
from app.schemas.profile import ProjectCreate, ProjectUpdate, ProjectOut
from app.services.chunker import chunk_project, chunk_resume, chunk_skill
from app.services.embedder import get_embedder
from app.services.vector_store import get_vector_store, ChunkMeta
from app.db.models import Resume, Skill

router = APIRouter(prefix="/projects", tags=["projects"])


async def _rebuild_index(user_id: UUID, db: AsyncSession) -> None:
    """Rebuild full FAISS index for a user from all their data."""
    all_chunks = []

    # Resume chunks
    res = await db.execute(select(Resume).where(Resume.user_id == user_id))
    resume = res.scalar_one_or_none()
    if resume and resume.extracted_text:
        all_chunks.extend(chunk_resume(resume.extracted_text, str(resume.id)))

    # Project chunks
    res = await db.execute(select(Project).where(Project.user_id == user_id))
    projects = res.scalars().all()
    for p in projects:
        all_chunks.extend(chunk_project(p.title, p.description or "", p.technologies or "", str(p.id)))

    # Skill chunks
    res = await db.execute(select(Skill).where(Skill.user_id == user_id))
    skills = res.scalars().all()
    for s in skills:
        all_chunks.extend(chunk_skill(s.skill_name, str(s.id)))

    if not all_chunks:
        store = get_vector_store()
        store.delete(user_id)
        return

    embedder = get_embedder()
    store = get_vector_store()

    texts = [c.text for c in all_chunks]
    vectors = await embedder.embed_many(texts)
    meta = [
        ChunkMeta(faiss_id=i, text=c.text, source=c.source, section=c.section, item_id=c.item_id)
        for i, c in enumerate(all_chunks)
    ]
    store.build(user_id, vectors, meta)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def add_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(user_id=current_user.id, **body.model_dump())
    db.add(project)
    await db.flush()
    await _rebuild_index(current_user.id, db)
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    return [ProjectOut.model_validate(p) for p in result.scalars().all()]


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)

    await _rebuild_index(current_user.id, db)
    return ProjectOut.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    await db.delete(project)
    await db.flush()
    await _rebuild_index(current_user.id, db)
