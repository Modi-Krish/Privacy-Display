from datetime import datetime, timezone
from uuid import UUID, uuid4
import firebase_admin
from firebase_admin import firestore
from app.services.db_service import (
    BaseDatabaseService, UserDBModel, ProfileDBModel, ResumeDBModel,
    ProjectDBModel, SkillDBModel, InterviewSessionDBModel, QuestionDBModel, ResponseDBModel
)

_firestore_client = None

def get_firestore_client():
    global _firestore_client
    if _firestore_client is None:
        if not firebase_admin._apps:
            from app.core.config import get_settings
            from firebase_admin import credentials
            import os
            import sys
            settings = get_settings()
            
            # Resolve path for PyInstaller (sys._MEIPASS) or normal env
            base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
            json_path = os.path.join(base_path, settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            
            if os.path.exists(json_path):
                cred = credentials.Certificate(json_path)
                firebase_admin.initialize_app(cred)
            else:
                # Fallback to absolute parent just in case
                alt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", settings.FIREBASE_SERVICE_ACCOUNT_JSON))
                if os.path.exists(alt_path):
                    cred = credentials.Certificate(alt_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()
        _firestore_client = firestore.client()
    return _firestore_client


def to_uuid(val) -> UUID:
    if not val:
        raise ValueError("Cannot convert empty value to UUID")
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


def to_datetime(val) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        return datetime.fromisoformat(val)
    return datetime.now(timezone.utc)  # fallback


class FirestoreDatabaseService(BaseDatabaseService):
    async def get_user_by_id(self, user_id: UUID, db: any = None) -> UserDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("users").document(str(user_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            return UserDBModel(
                id=to_uuid(data["id"]),
                email=data["email"],
                password_hash=data["password_hash"],
                is_active=data["is_active"],
                created_at=to_datetime(data["created_at"])
            )
        return None

    async def get_user_by_email(self, email: str, db: any = None) -> UserDBModel | None:
        client = get_firestore_client()
        docs = client.collection("users").where("email", "==", email).limit(1).stream()
        for doc in docs:
            data = doc.to_dict() or {}
            return UserDBModel(
                id=to_uuid(data["id"]),
                email=data["email"],
                password_hash=data["password_hash"],
                is_active=data["is_active"],
                created_at=to_datetime(data["created_at"])
            )
        return None

    async def create_user(self, email: str, password_hash: str, db: any = None) -> UserDBModel:
        client = get_firestore_client()
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(user_id),
            "email": email,
            "password_hash": password_hash,
            "is_active": True,
            "created_at": now
        }
        client.collection("users").document(str(user_id)).set(data)
        return UserDBModel(
            id=user_id,
            email=email,
            password_hash=password_hash,
            is_active=True,
            created_at=now
        )

    async def update_user_active(self, user_id: UUID, is_active: bool, db: any = None) -> UserDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("users").document(str(user_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            doc_ref.update({"is_active": is_active})
            data = snapshot.to_dict() or {}
            return UserDBModel(
                id=to_uuid(data["id"]),
                email=data["email"],
                password_hash=data["password_hash"],
                is_active=is_active,
                created_at=to_datetime(data["created_at"])
            )
        return None

    async def get_profile(self, user_id: UUID, db: any = None) -> ProfileDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("profiles").document(str(user_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            return ProfileDBModel(
                id=to_uuid(data["id"]),
                user_id=to_uuid(data["user_id"]),
                full_name=data.get("full_name"),
                summary=data.get("summary")
            )
        return None

    async def create_or_update_profile(self, user_id: UUID, full_name: str | None = None, summary: str | None = None, db: any = None) -> ProfileDBModel:
        client = get_firestore_client()
        doc_ref = client.collection("profiles").document(str(user_id))
        snapshot = doc_ref.get()
        
        if snapshot.exists:
            updates = {}
            if full_name is not None:
                updates["full_name"] = full_name
            if summary is not None:
                updates["summary"] = summary
            if updates:
                doc_ref.update(updates)
            data = doc_ref.get().to_dict() or {}
        else:
            profile_id = uuid4()
            data = {
                "id": str(profile_id),
                "user_id": str(user_id),
                "full_name": full_name,
                "summary": summary
            }
            doc_ref.set(data)
            
        return ProfileDBModel(
            id=to_uuid(data["id"]),
            user_id=to_uuid(data["user_id"]),
            full_name=data.get("full_name"),
            summary=data.get("summary")
        )

    async def get_resume(self, user_id: UUID, db: any = None) -> ResumeDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("resumes").document(str(user_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            return ResumeDBModel(
                id=to_uuid(data["id"]),
                user_id=to_uuid(data["user_id"]),
                file_name=data["file_name"],
                extracted_text=data.get("extracted_text"),
                uploaded_at=to_datetime(data["uploaded_at"])
            )
        return None

    async def create_resume(self, user_id: UUID, file_name: str, extracted_text: str | None, db: any = None) -> ResumeDBModel:
        client = get_firestore_client()
        resume_id = uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(resume_id),
            "user_id": str(user_id),
            "file_name": file_name,
            "extracted_text": extracted_text,
            "uploaded_at": now
        }
        client.collection("resumes").document(str(user_id)).set(data)
        return ResumeDBModel(
            id=resume_id,
            user_id=user_id,
            file_name=file_name,
            extracted_text=extracted_text,
            uploaded_at=now
        )

    async def delete_resume(self, user_id: UUID, db: any = None) -> None:
        client = get_firestore_client()
        client.collection("resumes").document(str(user_id)).delete()

    async def get_projects(self, user_id: UUID, db: any = None) -> list[ProjectDBModel]:
        client = get_firestore_client()
        docs = client.collection("projects").where("user_id", "==", str(user_id)).stream()
        results = []
        for doc in docs:
            data = doc.to_dict() or {}
            results.append(ProjectDBModel(
                id=to_uuid(data["id"]),
                user_id=to_uuid(data["user_id"]),
                title=data["title"],
                description=data.get("description"),
                technologies=data.get("technologies")
            ))
        return results

    async def get_project(self, project_id: UUID, user_id: UUID, db: any = None) -> ProjectDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("projects").document(str(project_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            if str(data.get("user_id")) == str(user_id):
                return ProjectDBModel(
                    id=to_uuid(data["id"]),
                    user_id=to_uuid(data["user_id"]),
                    title=data["title"],
                    description=data.get("description"),
                    technologies=data.get("technologies")
                )
        return None

    async def create_project(self, user_id: UUID, title: str, description: str | None = None, technologies: str | None = None, db: any = None) -> ProjectDBModel:
        client = get_firestore_client()
        project_id = uuid4()
        data = {
            "id": str(project_id),
            "user_id": str(user_id),
            "title": title,
            "description": description,
            "technologies": technologies
        }
        client.collection("projects").document(str(project_id)).set(data)
        return ProjectDBModel(
            id=project_id,
            user_id=user_id,
            title=title,
            description=description,
            technologies=technologies
        )

    async def update_project(self, project_id: UUID, user_id: UUID, title: str | None = None, description: str | None = None, technologies: str | None = None, db: any = None) -> ProjectDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("projects").document(str(project_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            if str(data.get("user_id")) == str(user_id):
                updates = {}
                if title is not None:
                    updates["title"] = title
                if description is not None:
                    updates["description"] = description
                if technologies is not None:
                    updates["technologies"] = technologies
                if updates:
                    doc_ref.update(updates)
                final_data = doc_ref.get().to_dict() or {}
                return ProjectDBModel(
                    id=to_uuid(final_data["id"]),
                    user_id=to_uuid(final_data["user_id"]),
                    title=final_data["title"],
                    description=final_data.get("description"),
                    technologies=final_data.get("technologies")
                )
        return None

    async def delete_project(self, project_id: UUID, user_id: UUID, db: any = None) -> None:
        client = get_firestore_client()
        doc_ref = client.collection("projects").document(str(project_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            if str(data.get("user_id")) == str(user_id):
                doc_ref.delete()

    async def get_skills(self, user_id: UUID, db: any = None) -> list[SkillDBModel]:
        client = get_firestore_client()
        docs = client.collection("skills").where("user_id", "==", str(user_id)).stream()
        results = []
        for doc in docs:
            data = doc.to_dict() or {}
            results.append(SkillDBModel(
                id=to_uuid(data["id"]),
                user_id=to_uuid(data["user_id"]),
                skill_name=data["skill_name"]
            ))
        return results

    async def get_skill(self, skill_id: UUID, user_id: UUID, db: any = None) -> SkillDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("skills").document(str(skill_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            if str(data.get("user_id")) == str(user_id):
                return SkillDBModel(
                    id=to_uuid(data["id"]),
                    user_id=to_uuid(data["user_id"]),
                    skill_name=data["skill_name"]
                )
        return None

    async def create_skill(self, user_id: UUID, skill_name: str, db: any = None) -> SkillDBModel:
        client = get_firestore_client()
        skill_id = uuid4()
        data = {
            "id": str(skill_id),
            "user_id": str(user_id),
            "skill_name": skill_name
        }
        client.collection("skills").document(str(skill_id)).set(data)
        return SkillDBModel(
            id=skill_id,
            user_id=user_id,
            skill_name=skill_name
        )

    async def delete_skill(self, skill_id: UUID, user_id: UUID, db: any = None) -> None:
        client = get_firestore_client()
        doc_ref = client.collection("skills").document(str(skill_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            if str(data.get("user_id")) == str(user_id):
                doc_ref.delete()

    async def get_interview_session(self, session_id: UUID, user_id: UUID, db: any = None) -> InterviewSessionDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("interview_sessions").document(str(session_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict() or {}
            if str(data.get("user_id")) == str(user_id):
                return InterviewSessionDBModel(
                    id=to_uuid(data["id"]),
                    user_id=to_uuid(data["user_id"]),
                    started_at=to_datetime(data["started_at"]),
                    ended_at=to_datetime(data["ended_at"]) if data.get("ended_at") else None
                )
        return None

    async def create_interview_session(self, user_id: UUID, db: any = None) -> InterviewSessionDBModel:
        client = get_firestore_client()
        session_id = uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(session_id),
            "user_id": str(user_id),
            "started_at": now,
            "ended_at": None
        }
        client.collection("interview_sessions").document(str(session_id)).set(data)
        return InterviewSessionDBModel(
            id=session_id,
            user_id=user_id,
            started_at=now,
            ended_at=None
        )

    async def end_interview_session(self, session_id: UUID, ended_at: datetime, db: any = None) -> InterviewSessionDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("interview_sessions").document(str(session_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            doc_ref.update({"ended_at": ended_at})
            data = doc_ref.get().to_dict() or {}
            return InterviewSessionDBModel(
                id=to_uuid(data["id"]),
                user_id=to_uuid(data["user_id"]),
                started_at=to_datetime(data["started_at"]),
                ended_at=ended_at
            )
        return None

    async def create_question(self, session_id: UUID, question_text: str, category: str | None = None, db: any = None) -> QuestionDBModel:
        client = get_firestore_client()
        question_id = uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": str(question_id),
            "session_id": str(session_id),
            "question_text": question_text,
            "category": category,
            "created_at": now
        }
        client.collection("questions").document(str(question_id)).set(data)
        return QuestionDBModel(
            id=question_id,
            session_id=session_id,
            question_text=question_text,
            category=category,
            created_at=now
        )

    async def update_question_category(self, question_id: UUID, category: str, db: any = None) -> QuestionDBModel | None:
        client = get_firestore_client()
        doc_ref = client.collection("questions").document(str(question_id))
        snapshot = doc_ref.get()
        if snapshot.exists:
            doc_ref.update({"category": category})
            data = doc_ref.get().to_dict() or {}
            return QuestionDBModel(
                id=to_uuid(data["id"]),
                session_id=to_uuid(data["session_id"]),
                question_text=data["question_text"],
                category=category,
                created_at=to_datetime(data["created_at"])
            )
        return None

    async def get_question_count(self, session_id: UUID, db: any = None) -> int:
        client = get_firestore_client()
        # count query
        count_query = client.collection("questions").where("session_id", "==", str(session_id)).count()
        snapshot = count_query.get()
        # extract count value from the count query response list
        return snapshot[0][0].value

    async def create_response(self, question_id: UUID, answer: str | None = None, confidence_score: float | None = None, generated_prompt: str | None = None, db: any = None) -> ResponseDBModel:
        client = get_firestore_client()
        resp_id = uuid4()
        data = {
            "id": str(resp_id),
            "question_id": str(question_id),
            "answer": answer,
            "confidence_score": confidence_score,
            "generated_prompt": generated_prompt
        }
        client.collection("responses").document(str(resp_id)).set(data)
        return ResponseDBModel(
            id=resp_id,
            question_id=question_id,
            answer=answer,
            confidence_score=confidence_score,
            generated_prompt=generated_prompt
        )
