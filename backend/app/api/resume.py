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
from app.services.resume_parser import extract_text_from_pdf, is_scanned_pdf
from app.services.indexing_service import rebuild_index_background, indexing_progress

settings = get_settings()
router = APIRouter(prefix="/resume", tags=["resume"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

@router.get("/progress")
async def get_indexing_progress(current_user: Any = Depends(get_current_user)):
    user_id_str = str(current_user.id)
    progress = indexing_progress.get(user_id_str)
    if not progress:
        return {"status": "idle"}
    return progress

@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate MIME type
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only PDF files are accepted")

    pdf_bytes = await file.read()

    if len(pdf_bytes) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    # Extract text
    extracted_text = extract_text_from_pdf(pdf_bytes)
    scanned = is_scanned_pdf(extracted_text)

    from app.services.db_service import get_db_service
    db_service = get_db_service()

    resume = await db_service.create_resume(
        current_user.id,
        file_name=file.filename or "resume.pdf",
        extracted_text=extracted_text if not scanned else None,
        db=db
    )

    # Rebuild full FAISS index in the background if we have text
    if not scanned and extracted_text:
        background_tasks.add_task(rebuild_index_background, current_user.id)

    if scanned:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "PDF appears to be scanned (image-only). Please copy-paste your resume text manually.",
        )

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
    await _rebuild_index(current_user.id, db)
