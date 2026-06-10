import sys
import traceback

def test_import(module_name):
    print(f"Testing import of {module_name}...", end="", flush=True)
    try:
        __import__(module_name)
        print(" SUCCESS", flush=True)
    except Exception as e:
        print(" FAILED", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()

if __name__ == "__main__":
    print(f"Python version: {sys.version}", flush=True)
    modules = [
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "asyncpg",
        "alembic",
        "numpy",
        "faiss",
        "fitz",  # PyMuPDF
        "faster_whisper",
        "sentence_transformers",
        "google.genai",
        "pytest",
        "aiosqlite",
    ]
    for module in modules:
        test_import(module)
    print("Import testing complete.", flush=True)
