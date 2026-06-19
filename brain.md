# REAI (Real-Time AI Privacy Display) - Project Brain

This is a comprehensive "brain file" designed to provide context for AI agents working on the `REAI` project. It contains the architecture, technology stack, directory structure, and essential notes about the system's behavior.

## 🚀 Project Overview

REAI is a privacy-focused, full-stack desktop application designed to assist software engineers during technical interviews or work sessions. It operates on a fast, asynchronous pipeline that:
1. Captures live meeting audio.
2. Transcribes it locally using STT (`faster-whisper`).
3. Performs semantic RAG (Retrieval-Augmented Generation) against a vector database of the user's resume, projects, and skills.
4. Generates contextual answers using Google Gemini.
5. Displays results via a React/Electron frontend that features advanced privacy settings (e.g., anti-screen share).

## 🛠️ Technology Stack

**Frontend (Desktop App)**
*   **Frameworks:** React 18, TypeScript, Vite.
*   **Desktop Shell:** Electron (uses `ContextBridge` for IPC sandboxing).
*   **State Management:** Zustand (Stores: `interviewStore`, `profileStore`, `settingsStore`).
*   **Styling:** CSS (`index.css`), Light-themed, glassmorphism UI.

**Backend (API Server)**
*   **Framework:** Python 3.11+, FastAPI.
*   **Database:** SQLite / PostgreSQL (accessed via SQLAlchemy/Alembic) + Firebase/Firestore for sync.
*   **AI - STT:** `faster-whisper` (Local execution, processes raw `io.BytesIO`).
*   **AI - LLM:** Google Gemini (`gemini-2.5-flash` via API).
*   **Vector Store (RAG):** FAISS with `sentence-transformers` (`all-MiniLM-L6-v2` embeddings).

## 📂 Architecture & Directory Structure

The project root is split between `frontend` and `backend`.

### `backend/` (FastAPI Server)
*   `.env` / `.env.example`: Environment variables and secrets.
*   `firebase_service_account.json`: Required for Firebase integration.
*   `requirements.txt`: Python dependencies.
*   `alembic/`: Database migrations.
*   `app/`
    *   `main.py`: Application entry point. Mounts routers and handles lifecycle.
    *   `api/`: FastAPI route handlers (Controllers).
        *   `audio.py`, `interview.py`, `realtime_ws.py` (WebSocket streams), `resume.py`, `projects.py`, `skills.py`.
    *   `services/`: Core business logic and AI/DB integrations.
        *   `streaming_stt.py` & `stt_service.py`: Audio processing and Whisper interactions.
        *   `gemini_service.py`: LLM API calls and prompting logic.
        *   `embedder.py`, `vector_store.py`, `retrieval.py`: RAG logic using FAISS.
        *   `firestore_db.py`, `sqlite_db.py`: Database operations.
        *   `interview_orchestrator.py`: Orchestrates the STT -> RAG -> LLM pipeline.
    *   `core/`: Config settings and security features.
    *   `db/`: SQLAlchemy models and session initialization.
    *   `schemas/`: Pydantic models for validation.

### `frontend/` (Electron + React)
*   `package.json`: NPM scripts (`dev:electron`, `build`) and dependencies.
*   `vite.config.ts`: Vite bundler configuration.
*   `src/`
    *   `electron/`: Electron main process logic.
        *   `main.ts`: Main process window creation, anti-spy (anti-screenshare) logic, and global shortcuts.
    *   `components/`: Reusable React UI components (e.g., `AppShell.tsx`, Custom Canvas Gauges).
    *   `pages/`: Application views (`InterviewPage.tsx`, `BrowserPage.tsx`, `ProfilePage.tsx`, `SettingsPage.tsx`).
    *   `store/`: Zustand state stores.
        *   `interviewStore.ts`: Manages live transcriptions and suggested answers.
        *   `profileStore.ts`: Manages user context (resume data, projects, skills).
        *   `settingsStore.ts`: Manages configurations like API keys and privacy toggles.
    *   `api/`: Axios / fetch clients communicating with the FastAPI backend.
    *   `index.css`: Global styles including glassmorphism tokens.
    *   `worklets/`: Audio processing or background Web Workers.

## 🔐 Core Privacy & Security Features
1.  **Anti-Screen Share (Anti-Spy):** Built into Electron. Blacks out the window and cursor in standard screensharing software (Zoom, Teams).
2.  **Global Privacy Hotkey:** `Ctrl + Shift + A + S` toggles privacy mode instantly.
3.  **Taskbar Stealth Mode:** Dynamically hides the app's taskbar icon to prevent it from showing in the active processes list.
4.  **Local Execution:** STT and Vector search are executed locally on the machine to prevent sensitive resume/audio data leaks (except for the final LLM prompt which goes to Gemini).

## 🚀 Running Locally

**Backend**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev:electron
```

## 🧠 AI Agent Instructions (When modifying this repo)
*   **Async First:** The backend is built heavily on `asyncio`. Use async DB sessions and `await` for I/O operations.
*   **Electron IPC:** When adding desktop features, remember the barrier between `electron/main.ts` and the React renderer. Use the established `ContextBridge` if new IPC channels are needed.
*   **Glassmorphism UI:** Keep styling consistent. Rely on CSS variables and existing layout components rather than hardcoding colors. Avoid standard Tailwind unless specifically bridging it to existing tokens.
*   **RAG Pipeline Changes:** If modifying the context fed to Gemini, update `backend/app/services/prompt_builder.py` and `retrieval.py`.
*   **Dependencies:** Do not introduce heavy native Node modules in the frontend unless necessary, as they complicate the Electron build process. Keep Python dependencies isolated to `requirements.txt`.
