import logging
from cryptography.fernet import Fernet
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_fernet = None

def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key_str = settings.ENCRYPTION_KEY
        try:
            # Fernet key must be 32 url-safe base64-encoded bytes
            key = key_str.encode()
            _fernet = Fernet(key)
        except Exception as e:
            logger.warning(
                "Invalid or missing ENCRYPTION_KEY in environment. "
                "Generating a temporary fallback key for execution.",
                extra={"error": str(e)}
            )
            # Fallback to generated key so the application doesn't crash immediately,
            # but logs a severe configuration warning.
            _fernet = Fernet(Fernet.generate_key())
    return _fernet

def encrypt_string(plain: str | None) -> str | None:
    if plain is None:
        return None
    try:
        fernet = get_fernet()
        return fernet.encrypt(plain.encode()).decode()
    except Exception as e:
        logger.error("Failed to encrypt string", extra={"error": str(e)})
        return plain

def decrypt_string(cipher: str | None) -> str | None:
    if cipher is None:
        return None
    try:
        fernet = get_fernet()
        return fernet.decrypt(cipher.encode()).decode()
    except Exception:
        # Fail-safe: if decryption fails (e.g. unencrypted legacy records), 
        # return the raw string to prevent app crashes.
        return cipher
