from fastapi import APIRouter

from app.core.app_state import app_state

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("/current")
def current_status() -> dict:
    return app_state.get_current_status()
