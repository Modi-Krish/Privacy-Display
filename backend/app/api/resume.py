"""
Resume API — upload, retrieve, delete. Triggers FAISS index rebuild.
"""
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, Resume
from app.schemas.profile import ResumeOut
from app.services.resume_parser import extract_text_from_pdf, is_scanned_pdf
from app.api.projects import _rebuild_index

settings = get_settings()
router = APIRouter(prefix="/resume", tags=["resume"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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

    # Remove existing resume record for user (one resume per user for MVP)
    await db.execute(delete(Resume).where(Resume.user_id == current_user.id))

    resume = Resume(
        user_id=current_user.id,
        file_name=file.filename or "resume.pdf",
        extracted_text=extracted_text if not scanned else None,
    )
    db.add(resume)
    await db.flush()

    # Rebuild full FAISS index if we have text
    if not scanned and extracted_text:
        await _rebuild_index(current_user.id, db)

    if scanned:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "PDF appears to be scanned (image-only). Please copy-paste your resume text manually.",
        )

    return ResumeOut.model_validate(resume)


@router.get("", response_model=ResumeOut)
async def get_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume uploaded")
    return ResumeOut.model_validate(resume)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(Resume).where(Resume.user_id == current_user.id))
    await db.flush()
    # Rebuild index from remaining data sources
    await _rebuild_index(current_user.id, db)
