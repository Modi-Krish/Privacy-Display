from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.services.db_service import (
    BaseDatabaseService, UserDBModel, ProfileDBModel, ResumeDBModel,
    ProjectDBModel, SkillDBModel, InterviewSessionDBModel, QuestionDBModel, ResponseDBModel
)
from app.db.models import User, Profile, Resume, Project, Skill, InterviewSession, Question, Response

class SQLiteDatabaseService(BaseDatabaseService):
    def _ensure_db(self, db: AsyncSession | None) -> AsyncSession:
        if db is None:
            raise ValueError("SQLAlchemy AsyncSession must be provided in SQLite mode")
        return db

    async def get_user_by_id(self, user_id: UUID, db: AsyncSession | None = None) -> UserDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return UserDBModel.model_validate(user) if user else None

    async def get_user_by_email(self, email: str, db: AsyncSession | None = None) -> UserDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        return UserDBModel.model_validate(user) if user else None

    async def create_user(self, email: str, password_hash: str, db: AsyncSession | None = None) -> UserDBModel:
        db = self._ensure_db(db)
        user = User(email=email, password_hash=password_hash)
        db.add(user)
        await db.flush()
        return UserDBModel.model_validate(user)

    async def update_user_active(self, user_id: UUID, is_active: bool, db: AsyncSession | None = None) -> UserDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_active = is_active
            await db.flush()
            return UserDBModel.model_validate(user)
        return None

    async def get_profile(self, user_id: UUID, db: AsyncSession | None = None) -> ProfileDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        return ProfileDBModel.model_validate(profile) if profile else None

    async def create_or_update_profile(self, user_id: UUID, full_name: str | None = None, summary: str | None = None, db: AsyncSession | None = None) -> ProfileDBModel:
        db = self._ensure_db(db)
        result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if not profile:
            profile = Profile(user_id=user_id, full_name=full_name, summary=summary)
            db.add(profile)
        else:
            if full_name is not None:
                profile.full_name = full_name
            if summary is not None:
                profile.summary = summary
        await db.flush()
        return ProfileDBModel.model_validate(profile)

    async def get_resume(self, user_id: UUID, db: AsyncSession | None = None) -> ResumeDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(Resume).where(Resume.user_id == user_id))
        resume = result.scalar_one_or_none()
        return ResumeDBModel.model_validate(resume) if resume else None

    async def create_resume(self, user_id: UUID, file_name: str, extracted_text: str | None, db: AsyncSession | None = None) -> ResumeDBModel:
        db = self._ensure_db(db)
        # Delete existing resume
        await db.execute(delete(Resume).where(Resume.user_id == user_id))
        resume = Resume(user_id=user_id, file_name=file_name, extracted_text=extracted_text)
        db.add(resume)
        await db.flush()
        return ResumeDBModel.model_validate(resume)

    async def delete_resume(self, user_id: UUID, db: AsyncSession | None = None) -> None:
        db = self._ensure_db(db)
        await db.execute(delete(Resume).where(Resume.user_id == user_id))
        await db.flush()

    async def get_projects(self, user_id: UUID, db: AsyncSession | None = None) -> list[ProjectDBModel]:
        db = self._ensure_db(db)
        result = await db.execute(select(Project).where(Project.user_id == user_id))
        return [ProjectDBModel.model_validate(p) for p in result.scalars().all()]

    async def get_project(self, project_id: UUID, user_id: UUID, db: AsyncSession | None = None) -> ProjectDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user_id))
        project = result.scalar_one_or_none()
        return ProjectDBModel.model_validate(project) if project else None

    async def create_project(self, user_id: UUID, title: str, description: str | None = None, technologies: str | None = None, db: AsyncSession | None = None) -> ProjectDBModel:
        db = self._ensure_db(db)
        project = Project(user_id=user_id, title=title, description=description, technologies=technologies)
        db.add(project)
        await db.flush()
        return ProjectDBModel.model_validate(project)

    async def update_project(self, project_id: UUID, user_id: UUID, title: str | None = None, description: str | None = None, technologies: str | None = None, db: AsyncSession | None = None) -> ProjectDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user_id))
        project = result.scalar_one_or_none()
        if project:
            if title is not None:
                project.title = title
            if description is not None:
                project.description = description
            if technologies is not None:
                project.technologies = technologies
            await db.flush()
            return ProjectDBModel.model_validate(project)
        return None

    async def delete_project(self, project_id: UUID, user_id: UUID, db: AsyncSession | None = None) -> None:
        db = self._ensure_db(db)
        await db.execute(delete(Project).where(Project.id == project_id, Project.user_id == user_id))
        await db.flush()

    async def get_skills(self, user_id: UUID, db: AsyncSession | None = None) -> list[SkillDBModel]:
        db = self._ensure_db(db)
        result = await db.execute(select(Skill).where(Skill.user_id == user_id))
        return [SkillDBModel.model_validate(s) for s in result.scalars().all()]

    async def get_skill(self, skill_id: UUID, user_id: UUID, db: AsyncSession | None = None) -> SkillDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
        skill = result.scalar_one_or_none()
        return SkillDBModel.model_validate(skill) if skill else None

    async def create_skill(self, user_id: UUID, skill_name: str, db: AsyncSession | None = None) -> SkillDBModel:
        db = self._ensure_db(db)
        skill = Skill(user_id=user_id, skill_name=skill_name)
        db.add(skill)
        await db.flush()
        return SkillDBModel.model_validate(skill)

    async def delete_skill(self, skill_id: UUID, user_id: UUID, db: AsyncSession | None = None) -> None:
        db = self._ensure_db(db)
        await db.execute(delete(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
        await db.flush()

    async def get_interview_session(self, session_id: UUID, user_id: UUID, db: AsyncSession | None = None) -> InterviewSessionDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id, InterviewSession.user_id == user_id))
        session = result.scalar_one_or_none()
        return InterviewSessionDBModel.model_validate(session) if session else None

    async def create_interview_session(self, user_id: UUID, db: AsyncSession | None = None) -> InterviewSessionDBModel:
        db = self._ensure_db(db)
        session = InterviewSession(user_id=user_id)
        db.add(session)
        await db.flush()
        return InterviewSessionDBModel.model_validate(session)

    async def end_interview_session(self, session_id: UUID, ended_at: datetime, db: AsyncSession | None = None) -> InterviewSessionDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.ended_at = ended_at
            await db.flush()
            return InterviewSessionDBModel.model_validate(session)
        return None

    async def create_question(self, session_id: UUID, question_text: str, category: str | None = None, db: AsyncSession | None = None) -> QuestionDBModel:
        db = self._ensure_db(db)
        question = Question(session_id=session_id, question_text=question_text, category=category)
        db.add(question)
        await db.flush()
        return QuestionDBModel.model_validate(question)

    async def update_question_category(self, question_id: UUID, category: str, db: AsyncSession | None = None) -> QuestionDBModel | None:
        db = self._ensure_db(db)
        result = await db.execute(select(Question).where(Question.id == question_id))
        question = result.scalar_one_or_none()
        if question:
            question.category = category
            await db.flush()
            return QuestionDBModel.model_validate(question)
        return None

    async def get_question_count(self, session_id: UUID, db: AsyncSession | None = None) -> int:
        db = self._ensure_db(db)
        count_result = await db.execute(select(func.count()).select_from(Question).where(Question.session_id == session_id))
        return count_result.scalar() or 0

    async def create_response(self, question_id: UUID, answer: str | None = None, confidence_score: float | None = None, generated_prompt: str | None = None, db: AsyncSession | None = None) -> ResponseDBModel:
        db = self._ensure_db(db)
        resp = Response(question_id=question_id, answer=answer, confidence_score=confidence_score, generated_prompt=generated_prompt)
        db.add(resp)
        await db.flush()
        return ResponseDBModel.model_validate(resp)
