from fastapi import APIRouter

from app.core.app_state import app_state

router = APIRouter(prefix="/api/vision-memory", tags=["vision-memory"])
compat_router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/status")
def vision_memory_status() -> dict:
    return app_state.get_memory_status()


@router.post("/reset")
def reset_vision_memory() -> dict:
    app_state.reset_memory()
    return {"ok": True, "message": "视觉记忆已重置"}


@compat_router.get("/status")
def memory_status() -> dict:
    return app_state.get_memory_status()


@compat_router.post("/reset")
def reset_memory() -> dict:
    app_state.reset_memory()
    return {"ok": True, "message": "视觉记忆已重置"}
