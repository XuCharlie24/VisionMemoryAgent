from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse

from app.services.camera_service import camera_service

router = APIRouter(prefix="/api/video", tags=["video"])


@router.get("/stream")
def video_stream() -> StreamingResponse:
    return StreamingResponse(
        camera_service.generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Access-Control-Allow-Origin": "*"},
    )


@router.get("/snapshot")
def video_snapshot() -> Response:
    return Response(
        content=camera_service.get_snapshot_frame(),
        media_type="image/jpeg",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
    )


@router.get("/gesture-frame")
def video_gesture_frame() -> Response:
    return Response(
        content=camera_service.get_gesture_frame(),
        media_type="image/jpeg",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store",
        },
    )
