from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health_routes, status_routes, video_routes, vision_memory_routes, vision_touch_routes
from app.core.settings import settings
from app.services.camera_service import camera_service
from app.services.vision_memory.memory_engine import memory_engine


def create_app() -> FastAPI:
    app = FastAPI(title="Vision Memory Agent", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_routes.router)
    app.include_router(video_routes.router)
    app.include_router(status_routes.router)
    app.include_router(vision_memory_routes.router)
    app.include_router(vision_memory_routes.compat_router)
    app.include_router(vision_touch_routes.router)

    @app.on_event("startup")
    def on_startup() -> None:
        camera_service.start()
        memory_engine.start(camera_service.get_frame)

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        memory_engine.stop()
        camera_service.stop()

    return app


app = create_app()
