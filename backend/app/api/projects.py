"""
Projects API — CRUD with FAISS re-embedding on create/update.
"""
from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.profile import ProjectCreate, ProjectUpdate, ProjectOut
from app.services.indexing_service import rebuild_index_background

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def add_project(
    body: ProjectCreate,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    project = await db_service.create_project(
        current_user.id,
        title=body.title,
        description=body.description,
        technologies=body.technologies,
        db=db
    )
    background_tasks.add_task(rebuild_index_background, current_user.id)
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
async def get_projects(
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    projects = await db_service.get_projects(current_user.id, db=db)
    return [ProjectOut.model_validate(p) for p in projects]


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    project = await db_service.update_project(
        project_id,
        current_user.id,
        title=body.title,
        description=body.description,
        technologies=body.technologies,
        db=db
    )
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    background_tasks.add_task(rebuild_index_background, current_user.id)
    return ProjectOut.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    project = await db_service.get_project(project_id, current_user.id, db=db)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    await db_service.delete_project(project_id, current_user.id, db=db)
    background_tasks.add_task(rebuild_index_background, current_user.id)
