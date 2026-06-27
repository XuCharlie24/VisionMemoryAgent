from fastapi import APIRouter

from app.services.camera_service import camera_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "project": "vision-memory-agent",
        "device": "RDK X3",
        "camera": camera_service.get_status(),
    }
