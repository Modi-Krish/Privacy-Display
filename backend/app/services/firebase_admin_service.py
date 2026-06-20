import os
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_initialized = False

try:
    json_b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")
    json_path = settings.FIREBASE_SERVICE_ACCOUNT_JSON
    
    if json_b64:
        import base64
        import json
        try:
            raw_json = base64.b64decode(json_b64).decode("utf-8")
            cred_dict = json.loads(raw_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _initialized = True
            logger.info("Firebase Admin SDK initialized successfully using Base64 environment variable.")
        except Exception as e:
            logger.error("Failed to initialize Firebase Admin SDK from Base64 environment variable", extra={"error": str(e)})
    
    if not _initialized and json_path:
        # Resolve relative path if necessary
        if not os.path.isabs(json_path):
            possible_paths = [
                os.path.abspath(json_path),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", json_path))
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    json_path = p
                    break
        
        if os.path.exists(json_path):
            cred = credentials.Certificate(json_path)
            firebase_admin.initialize_app(cred)
            _initialized = True
            logger.info(f"Firebase Admin SDK initialized successfully using certificate: {json_path}")
        else:
            logger.warning(f"Firebase service account file not found at: {json_path}. Firebase auth will be unavailable.")
    
    if not _initialized:
        logger.warning("No valid Firebase Admin SDK configuration found. Firebase auth will be unavailable.")
except Exception as e:
    logger.error("Failed to initialize Firebase Admin SDK", extra={"error": str(e)})


def verify_firebase_token(id_token: str) -> dict:
    """
    Verifies a Firebase ID token sent from the client.
    Returns the decoded token dictionary.
    """
    if not _initialized:
        raise ValueError("Firebase Admin SDK is not initialized. Please configure a valid service account JSON.")
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error("Failed to verify Firebase token", extra={"error": str(e)})
        raise ValueError(f"Invalid Firebase token: {str(e)}")
