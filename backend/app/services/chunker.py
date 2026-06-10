"""
Chunker Service — splits text into overlapping windows for embedding.
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str    # "resume" | "project" | "skill"
    section: str   # "education" | "experience" | "projects" | "skills" | "general"
    item_id: str   # DB UUID of the source record


def chunk_text(
    text: str,
    source: str,
    section: str,
    item_id: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """
    Sliding window character-based chunker.
    Returns [] for empty/very short text.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size to prevent infinite loops.")
    text = text.strip()
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append(Chunk(
            text=chunk_text,
            source=source,
            section=section,
            item_id=item_id,
        ))
        if end == len(words):
            break
        start = end - overlap   # slide back by overlap

    return chunks


def chunk_resume(extracted_text: str, resume_id: str) -> list[Chunk]:
    """
    Chunk a full resume text into sections using simple heuristics.
    """
    return chunk_text(
        text=extracted_text,
        source="resume",
        section="general",
        item_id=resume_id,
        chunk_size=512,
        overlap=64,
    )


def chunk_project(title: str, description: str, technologies: str, project_id: str) -> list[Chunk]:
    combined = f"Project: {title}\n{description or ''}\nTechnologies: {technologies or ''}"
    return chunk_text(combined, source="project", section="projects", item_id=project_id)


def chunk_skill(skill_name: str, skill_id: str) -> list[Chunk]:
    """Skills are short — returned as a single chunk."""
    return [Chunk(text=f"Skill: {skill_name}", source="skill", section="skills", item_id=skill_id)]
