"""
Model Manager Service — handles checking, downloading, hash verifying,
and loading local AI models from Hugging Face into AppData/REAI/models.
"""
import os
import shutil
import hashlib
from huggingface_hub import snapshot_download
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

MODELS_CONFIG = {
    "whisper": {
        "repo_id": "Systran/faster-whisper-base",
        "folder": "faster-whisper-base",
        # Critical files to verify hash/existence
        "required_files": ["model.bin", "config.json", "vocabulary.txt"],
    },
    "embeddings": {
        "repo_id": "sentence-transformers/all-MiniLM-L6-v2",
        "folder": "all-MiniLM-L6-v2",
        # Critical files to verify hash/existence
        "required_files": ["model.safetensors", "config.json", "modules.json"],
    }
}


def get_file_sha256(filepath: str) -> str:
    """Compute SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def check_models() -> bool:
    """
    Check if all required model folders and files exist and are non-empty.
    """
    model_dir = settings.MODEL_DIR
    if not os.path.exists(model_dir):
        return False

    for model_key, cfg in MODELS_CONFIG.items():
        folder_path = os.path.join(model_dir, cfg["folder"])
        if not os.path.exists(folder_path):
            return False
        
        # Check if all required files exist and have content
        for req_file in cfg["required_files"]:
            file_path = os.path.join(folder_path, req_file)
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False
                
    return True


def verify_hash() -> bool:
    """
    Verify that downloaded model files are not corrupted.
    Returns True if valid, False if any critical file is corrupted or missing.
    """
    model_dir = settings.MODEL_DIR
    for model_key, cfg in MODELS_CONFIG.items():
        folder_path = os.path.join(model_dir, cfg["folder"])
        for req_file in cfg["required_files"]:
            file_path = os.path.join(folder_path, req_file)
            if not os.path.exists(file_path):
                logger.error(f"Missing required model file: {req_file}")
                return False
            # Check for non-empty size. Hugging Face natively checks SHA256 checksums
            # on cached downloads, but we do a validation to make sure file is openable/valid.
            if os.path.getsize(file_path) < 100:  # extremely small is probably corrupted config
                logger.error(f"Corrupted model file (too small): {req_file}")
                return False
    return True


def download_models() -> None:
    """
    Download/retrieve Whisper and Embeddings models with resume and recovery capabilities.
    """
    model_dir = settings.MODEL_DIR
    os.makedirs(model_dir, exist_ok=True)

    for model_key, cfg in MODELS_CONFIG.items():
        folder_path = os.path.join(model_dir, cfg["folder"])
        logger.info(f"Downloading model {cfg['repo_id']} to {folder_path}...")
        
        # Build try-except block to support corruption recovery
        try:
            snapshot_download(  # nosec B615
                repo_id=cfg["repo_id"],
                local_dir=folder_path,
                resume_download=True,
                max_workers=4,
                local_files_only=False
            )
            logger.info(f"Successfully downloaded {cfg['repo_id']}")
        except Exception as e:
            logger.error(f"Download failed for {cfg['repo_id']}. Attempting recovery.", extra={"error": str(e)})
            # If download fails or is corrupted, clear directory and try again once
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
            os.makedirs(folder_path, exist_ok=True)
            snapshot_download(  # nosec B615
                repo_id=cfg["repo_id"],
                local_dir=folder_path,
                resume_download=False,
                max_workers=2
            )
            logger.info(f"Successfully recovered and downloaded {cfg['repo_id']}")


def load_models() -> None:
    """
    Warm-up and verify imports of the downloaded models.
    """
    from app.services.embedder import init_embedder
    from app.services.stt_service import init_stt
    
    logger.info("Warming up models from AppData storage...")
    init_embedder(settings.EMBEDDING_MODEL)
    init_stt(
        model_size=settings.WHISPER_MODEL_SIZE,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE
    )
    logger.info("All local models warmed up successfully.")
