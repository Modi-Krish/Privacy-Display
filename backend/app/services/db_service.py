import abc
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.core.config import get_settings

settings = get_settings()

class UserDBModel(BaseModel):
    id: UUID
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileDBModel(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str | None
    summary: str | None

    model_config = {"from_attributes": True}


class ResumeDBModel(BaseModel):
    id: UUID
    user_id: UUID
    file_name: str
    extracted_text: str | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ProjectDBModel(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None
    technologies: str | None

    model_config = {"from_attributes": True}


class SkillDBModel(BaseModel):
    id: UUID
    user_id: UUID
    skill_name: str

    model_config = {"from_attributes": True}


class InterviewSessionDBModel(BaseModel):
    id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class QuestionDBModel(BaseModel):
    id: UUID
    session_id: UUID
    question_text: str
    category: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResponseDBModel(BaseModel):
    id: UUID
    question_id: UUID
    answer: str | None
    confidence_score: float | None
    generated_prompt: str | None

    model_config = {"from_attributes": True}


class BaseDatabaseService(abc.ABC):
    @abc.abstractmethod
    async def get_user_by_id(self, user_id: UUID, db: any = None) -> UserDBModel | None:
        pass

    @abc.abstractmethod
    async def get_user_by_email(self, email: str, db: any = None) -> UserDBModel | None:
        pass

    @abc.abstractmethod
    async def create_user(self, email: str, password_hash: str, db: any = None) -> UserDBModel:
        pass

    @abc.abstractmethod
    async def update_user_active(self, user_id: UUID, is_active: bool, db: any = None) -> UserDBModel | None:
        pass

    @abc.abstractmethod
    async def get_profile(self, user_id: UUID, db: any = None) -> ProfileDBModel | None:
        pass

    @abc.abstractmethod
    async def create_or_update_profile(self, user_id: UUID, full_name: str | None = None, summary: str | None = None, db: any = None) -> ProfileDBModel:
        pass

    @abc.abstractmethod
    async def get_resume(self, user_id: UUID, db: any = None) -> ResumeDBModel | None:
        pass

    @abc.abstractmethod
    async def create_resume(self, user_id: UUID, file_name: str, extracted_text: str | None, db: any = None) -> ResumeDBModel:
        pass

    @abc.abstractmethod
    async def delete_resume(self, user_id: UUID, db: any = None) -> None:
        pass

    @abc.abstractmethod
    async def get_projects(self, user_id: UUID, db: any = None) -> list[ProjectDBModel]:
        pass

    @abc.abstractmethod
    async def get_project(self, project_id: UUID, user_id: UUID, db: any = None) -> ProjectDBModel | None:
        pass

    @abc.abstractmethod
    async def create_project(self, user_id: UUID, title: str, description: str | None = None, technologies: str | None = None, db: any = None) -> ProjectDBModel:
        pass

    @abc.abstractmethod
    async def update_project(self, project_id: UUID, user_id: UUID, title: str | None = None, description: str | None = None, technologies: str | None = None, db: any = None) -> ProjectDBModel | None:
        pass

    @abc.abstractmethod
    async def delete_project(self, project_id: UUID, user_id: UUID, db: any = None) -> None:
        pass

    @abc.abstractmethod
    async def get_skills(self, user_id: UUID, db: any = None) -> list[SkillDBModel]:
        pass

    @abc.abstractmethod
    async def get_skill(self, skill_id: UUID, user_id: UUID, db: any = None) -> SkillDBModel | None:
        pass

    @abc.abstractmethod
    async def create_skill(self, user_id: UUID, skill_name: str, db: any = None) -> SkillDBModel:
        pass

    @abc.abstractmethod
    async def delete_skill(self, skill_id: UUID, user_id: UUID, db: any = None) -> None:
        pass

    @abc.abstractmethod
    async def get_interview_session(self, session_id: UUID, user_id: UUID, db: any = None) -> InterviewSessionDBModel | None:
        pass

    @abc.abstractmethod
    async def create_interview_session(self, user_id: UUID, db: any = None) -> InterviewSessionDBModel:
        pass

    @abc.abstractmethod
    async def end_interview_session(self, session_id: UUID, ended_at: datetime, db: any = None) -> InterviewSessionDBModel | None:
        pass

    @abc.abstractmethod
    async def create_question(self, session_id: UUID, question_text: str, category: str | None = None, db: any = None) -> QuestionDBModel:
        pass

    @abc.abstractmethod
    async def update_question_category(self, question_id: UUID, category: str, db: any = None) -> QuestionDBModel | None:
        pass

    @abc.abstractmethod
    async def get_question_count(self, session_id: UUID, db: any = None) -> int:
        pass

    @abc.abstractmethod
    async def create_response(self, question_id: UUID, answer: str | None = None, confidence_score: float | None = None, generated_prompt: str | None = None, db: any = None) -> ResponseDBModel:
        pass


_db_service: BaseDatabaseService | None = None

def get_db_service() -> BaseDatabaseService:
    global _db_service
    if _db_service is None:
        provider = settings.DATABASE_PROVIDER.lower()
        if provider == "firestore":
            from app.services.firestore_db import FirestoreDatabaseService
            _db_service = FirestoreDatabaseService()
        else:
            from app.services.sqlite_db import SQLiteDatabaseService
            _db_service = SQLiteDatabaseService()
    return _db_service
