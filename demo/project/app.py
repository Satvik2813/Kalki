"""Demo application — simple API with authentication."""
import config
from auth import create_token, verify_token


def get_public_info() -> dict:
    """Public endpoint — no auth required."""
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running",
    }


def get_protected_data(token: str) -> dict:
    """Protected endpoint — requires a valid auth token."""
    result = verify_token(token)
    if not result["valid"]:
        return {"error": "Unauthorized", "status": 401}
    return {
        "user_id": result["user_id"],
        "data": "This is protected data that requires authentication.",
        "status": 200,
    }


def login(user_id: str) -> dict:
    """Login endpoint — creates an auth token."""
    try:
        token = create_token(user_id)
        return {"token": token, "user_id": user_id, "status": 200}
    except Exception as e:
        return {"error": str(e), "status": 500}
