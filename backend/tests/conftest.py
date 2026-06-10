import pytest
from unittest.mock import MagicMock, AsyncMock
import numpy as np
import uuid
from app.db.session import get_db
from app.main import app

# Mock embedder service initialization and methods
@pytest.fixture(autouse=True)
def mock_embedder(monkeypatch):
    import app.services.embedder as embedder
    
    mock_service = MagicMock()
    mock_service.load = MagicMock()
    mock_service.embed_many = AsyncMock(return_value=np.zeros((1, 384), dtype=np.float32))
    mock_service.embed_one = AsyncMock(return_value=np.zeros(384, dtype=np.float32))
    
    monkeypatch.setattr(embedder, "_embedder_instance", mock_service)
    
    def mock_init(*args, **kwargs):
        return mock_service
        
    monkeypatch.setattr(embedder, "init_embedder", mock_init)
    return mock_service

# Mock STT service initialization and methods
@pytest.fixture(autouse=True)
def mock_stt(monkeypatch):
    import app.services.stt_service as stt_service
    from app.services.stt_service import TranscriptionResult
    
    mock_service = MagicMock()
    mock_service.load = MagicMock()
    mock_service.transcribe = AsyncMock(return_value=TranscriptionResult(text="Mocked transcription", confidence=0.99, language="en"))
    mock_service.transcribe_b64 = AsyncMock(return_value=TranscriptionResult(text="Mocked transcription", confidence=0.99, language="en"))
    
    monkeypatch.setattr(stt_service, "_stt_instance", mock_service)
    
    def mock_init(*args, **kwargs):
        return mock_service
        
    monkeypatch.setattr(stt_service, "init_stt", mock_init)
    return mock_service

# Mock Gemini service initialization and methods
@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    import app.services.gemini_service as gemini_service
    
    mock_service = MagicMock()
    mock_service.classify = AsyncMock(return_value=("Technical", 0.95))
    mock_service.generate_answer = AsyncMock(return_value="Mocked Gemini answer response.")
    
    monkeypatch.setattr(gemini_service, "_gemini_instance", mock_service)
    
    def mock_init(*args, **kwargs):
        return mock_service
        
    monkeypatch.setattr(gemini_service, "init_gemini", mock_init)
    return mock_service

# Mock Database Session to support SQLite/in-memory style testing without Postgres dependency
class MockDbSession:
    def __init__(self):
        self.users = {}

    async def execute(self, query):
        query_str = str(query)
        mock_result = MagicMock()
        
        email = None
        try:
            compiled = query.compile()
            params = compiled.params
            for k, v in params.items():
                if isinstance(v, str) and "@" in v:
                    email = v
                    break
        except Exception:
            pass
            
        if not email:
            if "test@example.com" in query_str:
                email = "test@example.com"
                
        if email:
            if email in self.users:
                user_obj = self.users[email]
                mock_result.scalar_one_or_none.return_value = user_obj
                mock_result.scalars.return_value.all.return_value = [user_obj]
            else:
                mock_result.scalar_one_or_none.return_value = None
                mock_result.scalars.return_value.all.return_value = []
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
            
        return mock_result

    def add(self, instance):
        if hasattr(instance, "id") and getattr(instance, "id") is None:
            setattr(instance, "id", uuid.uuid4())
        if hasattr(instance, "created_at") and getattr(instance, "created_at") is None:
            from datetime import datetime, timezone
            setattr(instance, "created_at", datetime.now(timezone.utc))
        if hasattr(instance, "is_active") and getattr(instance, "is_active") is None:
            setattr(instance, "is_active", True)
            
        if instance.__class__.__name__ == "User":
            self.users[instance.email] = instance

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

@pytest.fixture(autouse=True)
def mock_database(monkeypatch):
    mock_db = MockDbSession()
    
    async def mock_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = mock_get_db
    yield mock_db
    app.dependency_overrides.pop(get_db, None)

# Mock subprocess.run during startup to prevent failing migrations on local Windows env
@pytest.fixture(autouse=True, scope="session")
def mock_subprocess(pytestconfig):
    import subprocess
    original_run = subprocess.run
    
    def mocked_run(args, **kwargs):
        if args and args[0] == "alembic":
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = "Mocked migration success"
            mock_res.stderr = ""
            return mock_res
        return original_run(args, **kwargs)
        
    subprocess.run = mocked_run
    yield
    subprocess.run = original_run

