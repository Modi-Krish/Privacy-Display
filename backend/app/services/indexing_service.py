import asyncio
import time
from typing import Dict, Any
from uuid import UUID
from app.db.session import AsyncSessionLocal

# Global in-memory store for indexing progress
# Key: user_id string, Value: dict with progress details
indexing_progress: Dict[str, Dict[str, Any]] = {}

async def rebuild_index_background(user_id: UUID) -> None:
    """Rebuild full FAISS index in the background with a dedicated DB session and progress tracking."""
    user_id_str = str(user_id)
    indexing_progress[user_id_str] = {
        "status": "processing",
        "progress_pct": 0,
        "current_file": "Initializing",
        "completed_items": 0,
        "total_items": 0,
        "time_remaining_sec": None,
        "error": None
    }
    
    start_time = time.time()
    
    try:
        async with AsyncSessionLocal() as db:
            from app.services.db_service import get_db_service
            db_service = get_db_service()
            all_chunks = []

            indexing_progress[user_id_str]["current_file"] = "Fetching Data"
            
            # Resume chunks
            resume = await db_service.get_resume(user_id, db=db)
            if resume and resume.extracted_text:
                from app.services.chunker import chunk_resume
                all_chunks.extend(chunk_resume(resume.extracted_text, str(resume.id)))

            # Project chunks
            projects = await db_service.get_projects(user_id, db=db)
            for p in projects:
                from app.services.chunker import chunk_project
                all_chunks.extend(chunk_project(p.title, p.description or "", p.technologies or "", str(p.id)))

            # Skill chunks
            skills = await db_service.get_skills(user_id, db=db)
            for s in skills:
                from app.services.chunker import chunk_skill
                all_chunks.extend(chunk_skill(s.skill_name, str(s.id)))

            if not all_chunks:
                from app.services.vector_store import get_vector_store
                store = get_vector_store()
                store.delete(user_id)
                indexing_progress[user_id_str]["status"] = "completed"
                indexing_progress[user_id_str]["progress_pct"] = 100
                return

            from app.services.embedder import get_embedder
            from app.services.vector_store import get_vector_store, ChunkMeta
            
            embedder = get_embedder()
            store = get_vector_store()

            texts = [c.text for c in all_chunks]
            total_items = len(texts)
            indexing_progress[user_id_str]["total_items"] = total_items
            indexing_progress[user_id_str]["current_file"] = "Generating Embeddings"
            
            # Batch process embeddings for granular progress
            batch_size = 5
            vectors = []
            
            for i in range(0, total_items, batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_vectors = await embedder.embed_many(batch_texts)
                vectors.extend(batch_vectors)
                
                completed = min(i + batch_size, total_items)
                indexing_progress[user_id_str]["completed_items"] = completed
                indexing_progress[user_id_str]["progress_pct"] = int((completed / total_items) * 100)
                
                # Estimate time remaining
                elapsed = time.time() - start_time
                if completed > 0:
                    time_per_item = elapsed / completed
                    remaining_items = total_items - completed
                    indexing_progress[user_id_str]["time_remaining_sec"] = int(time_per_item * remaining_items)
                    
                # Small sleep to yield to event loop
                await asyncio.sleep(0.01)

            indexing_progress[user_id_str]["current_file"] = "Saving Index"
            meta = [
                ChunkMeta(faiss_id=i, text=c.text, source=c.source, section=c.section, item_id=c.item_id)
                for i, c in enumerate(all_chunks)
            ]
            store.build(user_id, vectors, meta)
            
            indexing_progress[user_id_str]["status"] = "completed"
            indexing_progress[user_id_str]["progress_pct"] = 100
            indexing_progress[user_id_str]["current_file"] = "Done"
            indexing_progress[user_id_str]["time_remaining_sec"] = 0
            
    except Exception as e:
        import logging
        logging.error(f"Background indexing failed: {e}")
        indexing_progress[user_id_str]["status"] = "failed"
        indexing_progress[user_id_str]["error"] = str(e)
