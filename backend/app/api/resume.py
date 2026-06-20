"""
Resume API — upload, retrieve, delete. Triggers FAISS index rebuild.
"""
import uuid
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, Resume
from app.schemas.profile import ResumeOut
from app.services.indexing_service import rebuild_index_background, get_progress
from app.tasks.tasks import parse_and_chunk_resume_task
import base64

settings = get_settings()
router = APIRouter(prefix="/resume", tags=["resume"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

@router.get("/progress")
async def get_indexing_progress(current_user: Any = Depends(get_current_user)):
    progress = await get_progress(current_user.id)
    return progress


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check upload quota
    from app.core.quotas import check_upload_quota
    await check_upload_quota(current_user.id)

    # Validate MIME type
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only PDF files are accepted")

    pdf_bytes = await file.read()

    if len(pdf_bytes) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    from app.services.db_service import get_db_service
    from app.services.supabase_service import upload_file_to_storage, get_public_url
    import asyncio
    db_service = get_db_service()

    resume = await db_service.create_resume(
        current_user.id,
        file_name=file.filename or "resume.pdf",
        extracted_text=None,
        db=db
    )

    # Upload to Supabase Storage and save version
    try:
        storage_path = await asyncio.to_thread(
            upload_file_to_storage,
            "resumes",
            pdf_bytes,
            file.filename or "resume.pdf",
            str(current_user.id),
            file.content_type
        )
        public_url = get_public_url("resumes", storage_path)
        
        await db_service.create_resume_version(
            resume_id=resume.id,
            file_name=public_url,
            extracted_text=None,
            db=db
        )
    except Exception as e:
        print(f"Failed to upload to Supabase: {e}")

    # Dispatch to Celery task
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    parse_and_chunk_resume_task.delay(str(current_user.id), str(resume.id), pdf_b64)

    # Invalidate dashboard stats cache
    from app.core.redis import delete_cache
    await delete_cache(f"user_stats:{current_user.id}")

    return ResumeOut.model_validate(resume)


@router.get("", response_model=ResumeOut)
async def get_resume(
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    resume = await db_service.get_resume(current_user.id, db=db)
    if not resume:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume uploaded")
    return ResumeOut.model_validate(resume)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    await db_service.delete_resume(current_user.id, db=db)
    # Rebuild index from remaining data sources
    rebuild_index_background(current_user.id)

    # Invalidate dashboard stats cache
    from app.core.redis import delete_cache
    await delete_cache(f"user_stats:{current_user.id}")
