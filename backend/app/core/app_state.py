from app.services.camera_service import camera_service
from app.services.vision_memory.memory_engine import memory_engine
from app.services.vision_touch.gesture_engine import gesture_engine


FRONTEND_TOUCH_STATUS = {
    "enabled": True,
    "tracking": False,
    "tracking_mode": "frontend",
    "state": "FRONTEND_CONTROLLED",
    "gesture": "none",
    "gesture_action": "none",
    "action": "none",
    "cursor": {"x": 0.5, "y": 0.5, "z": 0, "depth_level": "far"},
    "hand": None,
    "hand_active": False,
    "hand_ready": False,
    "metrics": {"fps": 0, "latency_ms": 0, "stable_frames": 0, "click_count": 0},
    "message": "手势由前端本地模型处理",
    "interaction": {
        "hand_active": False,
        "hand_ready": False,
        "hand_state": "FRONTEND_CONTROLLED",
        "gesture_action": "none",
        "message": "手势由前端本地模型处理",
        "debug": {
            "hand_source": "frontend",
            "hand_model_loaded": False,
            "reject_reason": "frontend_controlled",
        },
    },
}


class AppState:
    def get_current_status(self) -> dict:
        touch_status = self.get_touch_status()
        memory_status = memory_engine.get_status(compact=True)
        memory_status["interaction"] = touch_status.get("interaction", {})
        memory_status["performance"] = {
            **camera_service.get_metrics(),
            **memory_status.get("performance", {}),
        }
        return {
            "camera": camera_service.get_status(),
            "vision_memory": memory_status,
            "vision_touch": touch_status,
        }

    def get_memory_status(self) -> dict:
        touch_status = self.get_touch_status()
        memory_status = memory_engine.get_status(camera=camera_service.get_status())
        memory_status["interaction"] = touch_status.get("interaction", {})
        memory_status["performance"] = {
            **camera_service.get_metrics(),
            **memory_status.get("performance", {}),
        }
        return memory_status

    def reset_memory(self) -> None:
        memory_engine.reset()
        gesture_engine.reset_interaction()

    def get_touch_status(self) -> dict:
        return {
            **FRONTEND_TOUCH_STATUS,
            "interaction": FRONTEND_TOUCH_STATUS["interaction"].copy(),
        }

    def get_touch_config(self) -> dict:
        return gesture_engine.get_config()

    def update_touch_config(self, update: dict) -> dict:
        return gesture_engine.update_config(update)


app_state = AppState()
