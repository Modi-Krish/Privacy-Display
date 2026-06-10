from pydantic import BaseModel
from uuid import UUID


# ── Resume ────────────────────────────────────────────────────────────────────

class ResumeOut(BaseModel):
    id: UUID
    file_name: str
    extracted_text: str | None

    model_config = {"from_attributes": True}


# ── Project ───────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str
    description: str | None = None
    technologies: str | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    technologies: str | None = None


class ProjectOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    technologies: str | None

    model_config = {"from_attributes": True}


# ── Skill ─────────────────────────────────────────────────────────────────────

class SkillCreate(BaseModel):
    skill_name: str


class SkillOut(BaseModel):
    id: UUID
    skill_name: str

    model_config = {"from_attributes": True}
