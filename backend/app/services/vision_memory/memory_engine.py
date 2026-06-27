import threading
import time
from datetime import datetime

from app.services.vision_memory.memory_store import MemoryStore
from app.services.vision_memory.object_tracker import ObjectTracker


DEMO_SMOOTH_MODE = True
FAST_INFER_INTERVAL_SECONDS = 2.0
BALANCED_INFER_INTERVAL_SECONDS = 2.5
MEDIUM_INFER_INTERVAL_SECONDS = 3.0
SLOW_INFER_INTERVAL_SECONDS = 4.0
DEFAULT_INFER_INTERVAL_SECONDS = MEDIUM_INFER_INTERVAL_SECONDS
FAST_INFER_MS = 500
MEDIUM_INFER_MS = 900
SLOW_INFER_MS = 1500


class MemoryEngine:
    def __init__(self) -> None:
        self._tracker = ObjectTracker()
        self._store = MemoryStore()
        self._latest_event = "视觉记忆等待新的画面变化"
        self._last_update = 0.0
        self._last_duration_ms = 0
        self._object_count = 0
        self._last_candidates: list[dict] = []
        self._version = 0
        self._infer_times: list[float] = []
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._frame_getter = None
        self._infer_interval = DEFAULT_INFER_INTERVAL_SECONDS
        self._detection_cache = {
            "detections": [],
            "last_infer_time": None,
            "infer_latency_ms": 0,
            "model_fps": 0,
            "model_loaded": self._tracker.detector_status().get("object_model_loaded", False),
        }

    def start(self, frame_getter) -> None:
        if self._running:
            return
        self._frame_getter = frame_getter
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _worker_loop(self) -> None:
        while self._running:
            if self._frame_getter is None:
                time.sleep(0.1)
                continue
            now = time.time()
            if now - self._last_update < self._infer_interval:
                time.sleep(0.05)
                continue
            frame = self._frame_getter()
            if frame is None:
                time.sleep(0.1)
                continue
            self.update(frame, hand_active=False)
            with self._lock:
                latency_ms = self._last_duration_ms
                if latency_ms > SLOW_INFER_MS:
                    self._infer_interval = SLOW_INFER_INTERVAL_SECONDS
                elif latency_ms > MEDIUM_INFER_MS:
                    self._infer_interval = MEDIUM_INFER_INTERVAL_SECONDS
                elif latency_ms > FAST_INFER_MS:
                    self._infer_interval = BALANCED_INFER_INTERVAL_SECONDS
                else:
                    self._infer_interval = FAST_INFER_INTERVAL_SECONDS

    def update(self, frame, hand_active: bool = False) -> None:
        started = time.time()
        candidates = self._tracker.process_frame(frame, hand_active=hand_active)
        finished = time.time()
        duration_ms = int((finished - started) * 1000)
        with self._lock:
            self._last_update = started
            self._infer_times = [item for item in self._infer_times if finished - item <= 1.0]
            self._infer_times.append(finished)
            self._last_candidates = candidates
            self._object_count = len(candidates)
            changed = False
            for candidate in candidates:
                obj, is_new = self._store.add_or_update_object(candidate, hand_active=hand_active)
                if obj is None:
                    continue
                changed = True
                label = obj.get("label")
                if is_new and label != "person":
                    self._latest_event = f"发现新的{obj['label_zh']}：{obj['position']}"
                elif label != "person" and obj["position"] == "画面中央":
                    self._latest_event = f"持续观察画面中央的{obj['label_zh']}"
                elif label != "person":
                    self._latest_event = f"{obj['label_zh']}移动到{obj['position']}"
            self._last_duration_ms = duration_ms
            self._detection_cache = {
                "detections": [item.copy() for item in candidates],
                "last_infer_time": datetime.now().isoformat(timespec="seconds"),
                "infer_latency_ms": duration_ms,
                "model_fps": round(1000 / duration_ms, 2) if duration_ms else 0,
                "model_loaded": self._tracker.detector_status().get("object_model_loaded", False),
            }
            if changed:
                self._version += 1

    def get_status(self, camera: str = "online", compact: bool = False) -> dict:
        started = time.time()
        with self._lock:
            memories = self._store.get_snapshot()
            latest_memory = self._select_latest_memory(memories)
            detector_status = self.detector_status()
            now = time.time()
            payload = {
                "version": self._version,
                "enabled": True,
                "object_count": self._object_count,
                "memory_count": len(memories),
                "latest_memory": latest_memory,
                "latest_event": self._latest_event,
                "message": "视觉记忆运行中",
                "detector_status": detector_status,
                "detection_cache": self._detection_cache.copy(),
                "performance": {
                    "demo_smooth_mode": DEMO_SMOOTH_MODE,
                    "smooth_mode": DEMO_SMOOTH_MODE,
                    "detector_fps": round(len([item for item in self._infer_times if now - item <= 1.0]), 1),
                    "detector_latency_ms": self._last_duration_ms,
                    "detector_interval_ms": int(self._infer_interval * 1000),
                    "memory_update_ms": self._last_duration_ms,
                    "status_latency_ms": 0,
                },
                "debug": {
                    "memory_update_ms": self._last_duration_ms,
                    "recognizer": self._tracker.get_profile(),
                    "pending_count": self._store.get_pending_count(),
                    "recognition_interval_ms": int(self._infer_interval * 1000),
                    "async_worker": self._running,
                },
            }
        if not compact:
            payload["camera"] = camera
            payload["camera_status"] = camera
            payload["memories"] = memories
            payload["objects"] = memories
        payload["performance"]["status_latency_ms"] = int((time.time() - started) * 1000)
        return payload

    def reset(self) -> None:
        with self._lock:
            self._store.reset()
            self._object_count = 0
            self._last_candidates = []
            self._latest_event = "视觉记忆等待新的画面变化"
            self._detection_cache["detections"] = []
            self._version += 1

    def get_object_exclusions(self) -> list[dict]:
        exclusions = []
        with self._lock:
            candidates = [item.copy() for item in self._last_candidates]
        for item in candidates:
            if item.get("bbox") and item.get("label") not in {"unknown"}:
                exclusions.append({
                    "bbox": item["bbox"],
                    "label": item.get("label"),
                    "label_zh": item.get("label_zh"),
                })
        return exclusions[:8]

    def detector_status(self) -> dict:
        status = self._tracker.detector_status()
        status.update({
            "async_worker": self._running,
            "infer_interval_ms": int(self._infer_interval * 1000),
            "detector_interval_ms": int(self._infer_interval * 1000),
            "infer_latency_ms": self._last_duration_ms,
            "last_infer_time": self._detection_cache.get("last_infer_time"),
            "cached_detection_count": len(self._detection_cache.get("detections", [])),
            "model_fps": self._detection_cache.get("model_fps", 0),
        })
        return status

    def _select_latest_memory(self, memories: list[dict]) -> dict | None:
        if not memories:
            return None
        for item in memories[:6]:
            if item.get("label") != "person":
                return item
        return memories[0]


memory_engine = MemoryEngine()
