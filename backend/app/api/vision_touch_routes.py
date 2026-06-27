from fastapi import APIRouter

from app.core.app_state import app_state
from app.core.schemas import VisionTouchConfigUpdate

router = APIRouter(prefix="/api/vision-touch", tags=["vision-touch"])


@router.get("/status")
def vision_touch_status() -> dict:
    return app_state.get_touch_status()


@router.get("/config")
def vision_touch_config() -> dict:
    return app_state.get_touch_config()


@router.post("/config")
def update_vision_touch_config(update: VisionTouchConfigUpdate) -> dict:
    return app_state.update_touch_config(update.dict(exclude_none=True))
