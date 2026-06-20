import asyncio
import json
import hashlib
import uuid
import logging
from typing import List, Dict, Any
from sqlalchemy import select, delete

from app.tasks.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.db.models import Resume, ResumeChunk, Project, Skill
from app.services.resume_parser import extract_text_from_pdf, is_scanned_pdf
from app.services.chunker import chunk_resume, chunk_project, chunk_skill
from app.services.embedder import get_embedder, init_embedder
from app.core.config import get_settings
import redis

logger = logging.getLogger(__name__)
settings = get_settings()

def _get_redis_sync():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def update_progress(user_id: str, data: Dict[str, Any]):
    try:
        r = _get_redis_sync()
        key = f"indexing_progress:{user_id}"
        current = r.get(key)
        progress = json.loads(current) if current else {}
        progress.update(data)
        r.set(key, json.dumps(progress), ex=3600)
    except Exception as e:
        logger.error(f"Failed to update progress in Redis: {e}")

def get_or_init_worker_embedder():
    try:
        return get_embedder()
    except RuntimeError:
        return init_embedder(settings.EMBEDDING_MODEL)

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)

@celery_app.task(name="app.tasks.tasks.parse_and_chunk_resume_task")
def parse_and_chunk_resume_task(user_id: str, resume_id: str, file_bytes_b64: str):
    user_uuid = uuid.UUID(user_id)
    resume_uuid = uuid.UUID(resume_id)
    
    update_progress(user_id, {
        "status": "processing",
        "progress_pct": 10,
        "current_file": "Extracting text from PDF",
        "completed_items": 0,
        "total_items": 0,
        "error": None
    })
    
    try:
        import base64
        file_bytes = base64.b64decode(file_bytes_b64)
        extracted_text = extract_text_from_pdf(file_bytes)
        
        if not extracted_text or is_scanned_pdf(extracted_text):
            raise ValueError("PDF appears to be scanned or empty.")
        
        # Save extracted text to DB
        async def save_text():
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Resume).where(Resume.id == resume_uuid))
                resume = result.scalar_one_or_none()
                if resume:
                    resume.extracted_text = extracted_text
                    await db.commit()
        
        run_async(save_text())
        
        # Now chunk it
        chunks = chunk_resume(extracted_text, resume_id)
        
        # Format chunks to pass to the next task
        chunks_data = [
            {
                "text": c.text,
                "source": c.source,
                "section": c.section,
                "item_id": c.item_id
            } for c in chunks
        ]
        
        update_progress(user_id, {
            "progress_pct": 30,
            "current_file": "Queuing embedding generation"
        })
        
        # Dispatch embedding task
        generate_embeddings_and_index_task.delay(user_id, chunks_data, resume_id)
        
    except Exception as e:
        logger.error(f"Failed in parse_and_chunk_resume_task: {e}")
        update_progress(user_id, {
            "status": "failed",
            "error": str(e)
        })
        raise

@celery_app.task(name="app.tasks.tasks.generate_embeddings_and_index_task")
def generate_embeddings_and_index_task(user_id: str, chunks_data: List[Dict[str, Any]], resume_id: str = None):
    user_uuid = uuid.UUID(user_id)
    resume_uuid = uuid.UUID(resume_id) if resume_id else None
    
    update_progress(user_id, {
        "status": "processing",
        "progress_pct": 40,
        "current_file": "Generating embeddings",
        "total_items": len(chunks_data),
        "completed_items": 0
    })
    
    try:
        embedder = get_or_init_worker_embedder()
        
        # Deduplication and embedding logic
        async def process_chunks():
            async with AsyncSessionLocal() as db:
                for i, chunk_data in enumerate(chunks_data):
                    chunk_text = chunk_data["text"]
                    content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                    
                    # Deduplication: Check if this content_hash already exists in resume_chunks
                    stmt = select(ResumeChunk.embedding).where(ResumeChunk.content_hash == content_hash).limit(1)
                    res = await db.execute(stmt)
                    existing_embedding = res.scalar_one_or_none()
                    
                    if existing_embedding is not None:
                        embedding_vector = existing_embedding
                    else:
                        embedding_vector = await embedder.embed_one(chunk_text)
                    
                    # Create new chunk record
                    new_chunk = ResumeChunk(
                        id=uuid.uuid4(),
                        user_id=user_uuid,
                        resume_id=resume_uuid,
                        chunk_text=chunk_text,
                        embedding=embedding_vector,
                        source=chunk_data["source"],
                        section=chunk_data["section"],
                        item_id=chunk_data.get("item_id"),
                        content_hash=content_hash
                    )
                    db.add(new_chunk)
                    
                    # Update progress every few items
                    if (i + 1) % 5 == 0 or (i + 1) == len(chunks_data):
                        pct = 40 + int(((i + 1) / len(chunks_data)) * 50)
                        update_progress(user_id, {
                            "progress_pct": pct,
                            "completed_items": i + 1
                        })
                
                await db.commit()
                
        run_async(process_chunks())
        
        update_progress(user_id, {
            "status": "completed",
            "progress_pct": 100,
            "current_file": "Done",
            "time_remaining_sec": 0
        })
        
    except Exception as e:
        logger.error(f"Failed in generate_embeddings_and_index_task: {e}")
        update_progress(user_id, {
            "status": "failed",
            "error": str(e)
        })
        raise

@celery_app.task(name="app.tasks.tasks.rebuild_rag_index_task")
def rebuild_rag_index_task(user_id: str):
    user_uuid = uuid.UUID(user_id)
    
    update_progress(user_id, {
        "status": "processing",
        "progress_pct": 10,
        "current_file": "Rebuilding index - fetching user data",
        "completed_items": 0,
        "total_items": 0,
        "error": None
    })
    
    try:
        async def fetch_and_rebuild():
            async with AsyncSessionLocal() as db:
                # Fetch resumes
                resumes_res = await db.execute(select(Resume).where(Resume.user_id == user_uuid))
                resumes = resumes_res.scalars().all()
                
                # Fetch projects
                projects_res = await db.execute(select(Project).where(Project.user_id == user_uuid))
                projects = projects_res.scalars().all()
                
                # Fetch skills
                skills_res = await db.execute(select(Skill).where(Skill.user_id == user_uuid))
                skills = skills_res.scalars().all()
                
                # Delete all existing chunks for user first
                await db.execute(delete(ResumeChunk).where(ResumeChunk.user_id == user_uuid))
                await db.commit()
                
                all_chunks_data = []
                
                # Resume chunks
                for r in resumes:
                    if r.extracted_text:
                        chunks = chunk_resume(r.extracted_text, str(r.id))
                        all_chunks_data.extend([
                            {
                                "text": c.text,
                                "source": c.source,
                                "section": c.section,
                                "item_id": c.item_id,
                                "resume_id": str(r.id)
                            } for c in chunks
                        ])
                
                # Project chunks
                for p in projects:
                    chunks = chunk_project(p.title, p.description or "", p.technologies or "", str(p.id))
                    all_chunks_data.extend([
                        {
                            "text": c.text,
                            "source": c.source,
                            "section": c.section,
                            "item_id": c.item_id,
                            "resume_id": None
                        } for c in chunks
                    ])
                
                # Skill chunks
                for s in skills:
                    chunks = chunk_skill(s.skill_name, str(s.id))
                    all_chunks_data.extend([
                        {
                            "text": c.text,
                            "source": c.source,
                            "section": c.section,
                            "item_id": c.item_id,
                            "resume_id": None
                        } for c in chunks
                    ])
                
                return all_chunks_data
        
        chunks_data = run_async(fetch_and_rebuild())
        
        if not chunks_data:
            update_progress(user_id, {
                "status": "completed",
                "progress_pct": 100,
                "current_file": "Done (No data to index)",
                "time_remaining_sec": 0
            })
            return
            
        generate_embeddings_and_index_task(user_id, chunks_data)
        
    except Exception as e:
        logger.error(f"Failed in rebuild_rag_index_task: {e}")
        update_progress(user_id, {
            "status": "failed",
            "error": str(e)
        })
        raise
