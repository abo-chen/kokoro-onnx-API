from fastapi import HTTPException, Request

from app.config import settings


def openai_error(error_type: str, code: str | None = None, message: str = "") -> dict:
    return {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": code,
        }
    }


async def verify_api_key(request: Request) -> None:
    if not settings.AUTH_ENABLED:
        return

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=openai_error("authentication_error", "invalid_api_key", "Invalid or missing API key."),
        )

    token = auth[7:]
    if token != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail=openai_error("authentication_error", "invalid_api_key", "Invalid API key."),
        )
