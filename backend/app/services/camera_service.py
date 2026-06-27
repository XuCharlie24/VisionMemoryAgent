import threading
import time
from collections import deque
from typing import Generator

import cv2
import numpy as np

from app.core.settings import settings


DEMO_SMOOTH_MODE = True
STREAM_SIZE = (480, 360)
STREAM_JPEG_QUALITY = 58
STREAM_TARGET_FPS = 12
SNAPSHOT_SIZE = (640, 480)
SNAPSHOT_JPEG_QUALITY = 68
GESTURE_FRAME_SIZE = (256, 192)
GESTURE_FRAME_JPEG_QUALITY = 45


class CameraService:
    def __init__(self) -> None:
        self._capture = None
        self._frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._status = "offline"
        self._last_open_attempt = 0.0
        self._last_frame_at = 0.0
        self._read_times = deque(maxlen=60)
        self._stream_times = deque(maxlen=60)
        self._snapshot_times = deque(maxlen=60)
        self._gesture_times = deque(maxlen=60)
        self._stream_encode_ms = deque(maxlen=20)
        self._snapshot_encode_ms = deque(maxlen=20)
        self._gesture_encode_ms = deque(maxlen=20)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._capture:
            self._capture.release()
            self._capture = None

    def _open_camera(self) -> bool:
        now = time.time()
        if now - self._last_open_attempt < 2:
            return False
        self._last_open_attempt = now
        cap = cv2.VideoCapture(settings.camera_device)
        if not cap.isOpened():
            self._status = "offline"
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
        cap.set(cv2.CAP_PROP_FPS, settings.camera_fps)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._capture = cap
        self._status = "online"
        return True

    def _read_loop(self) -> None:
        while self._running:
            if self._capture is None and not self._open_camera():
                time.sleep(0.2)
                continue
            ok, frame = self._capture.read()
            if not ok or frame is None:
                self._status = "offline"
                self._capture.release()
                self._capture = None
                time.sleep(0.2)
                continue
            self._status = "online"
            with self._lock:
                self._frame = frame
                self._last_frame_at = time.time()
                self._read_times.append(self._last_frame_at)
            time.sleep(0.005)

    def get_frame(self):
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def get_jpeg_frame(self, quality: int = 70, max_size: tuple[int, int] | None = None, metric: str = "snapshot") -> bytes:
        frame = self.get_frame()
        if frame is None:
            frame = self._placeholder_frame()
        if max_size is not None:
            frame = self._resize_to_fit(frame, max_size)
        started = time.time()
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        duration_ms = int((time.time() - started) * 1000)
        self._record_encode(metric, duration_ms)
        if not ok:
            return b""
        return encoded.tobytes()

    def generate_mjpeg(self) -> Generator[bytes, None, None]:
        while True:
            jpeg = self.get_jpeg_frame(quality=STREAM_JPEG_QUALITY, max_size=STREAM_SIZE, metric="stream")
            self._stream_times.append(time.time())
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            time.sleep(1 / STREAM_TARGET_FPS)

    def get_status(self) -> str:
        return self._status

    def get_snapshot_frame(self) -> bytes:
        self._snapshot_times.append(time.time())
        return self.get_jpeg_frame(quality=SNAPSHOT_JPEG_QUALITY, max_size=SNAPSHOT_SIZE, metric="snapshot")

    def get_gesture_frame(self) -> bytes:
        self._gesture_times.append(time.time())
        return self.get_jpeg_frame(quality=GESTURE_FRAME_JPEG_QUALITY, max_size=GESTURE_FRAME_SIZE, metric="gesture")

    def get_metrics(self) -> dict:
        now = time.time()
        with self._lock:
            latest_age_ms = int((now - self._last_frame_at) * 1000) if self._last_frame_at else None
        return {
            "demo_smooth_mode": DEMO_SMOOTH_MODE,
            "smooth_mode": DEMO_SMOOTH_MODE,
            "camera_fps": self._rate(self._read_times, now),
            "stream_fps": self._rate(self._stream_times, now),
            "stream_encode_ms": self._avg(self._stream_encode_ms),
            "stream_width": STREAM_SIZE[0],
            "stream_height": STREAM_SIZE[1],
            "stream_target_fps": STREAM_TARGET_FPS,
            "stream_jpeg_quality": STREAM_JPEG_QUALITY,
            "snapshot_requests_per_sec": self._rate(self._snapshot_times, now),
            "gesture_frame_requests_per_sec": self._rate(self._gesture_times, now),
            "gesture_frame_fps": self._rate(self._gesture_times, now),
            "snapshot_encode_ms": self._avg(self._snapshot_encode_ms),
            "gesture_frame_encode_ms": self._avg(self._gesture_encode_ms),
            "gesture_frame_width": GESTURE_FRAME_SIZE[0],
            "gesture_frame_height": GESTURE_FRAME_SIZE[1],
            "gesture_frame_jpeg_quality": GESTURE_FRAME_JPEG_QUALITY,
            "latest_frame_age_ms": latest_age_ms,
        }

    def _resize_to_fit(self, frame, max_size: tuple[int, int]):
        max_width, max_height = max_size
        height, width = frame.shape[:2]
        scale = min(max_width / max(width, 1), max_height / max(height, 1), 1.0)
        if scale >= 1.0:
            return frame
        return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

    def _record_encode(self, metric: str, duration_ms: int) -> None:
        if metric == "stream":
            self._stream_encode_ms.append(duration_ms)
        elif metric == "gesture":
            self._gesture_encode_ms.append(duration_ms)
        else:
            self._snapshot_encode_ms.append(duration_ms)

    def _rate(self, values, now: float) -> float:
        while values and now - values[0] > 1.0:
            values.popleft()
        return round(len(values), 1)

    def _avg(self, values) -> int:
        if not values:
            return 0
        return int(sum(values) / len(values))

    def _placeholder_frame(self):
        frame = np.zeros((settings.camera_height, settings.camera_width, 3), dtype=np.uint8)
        cv2.putText(frame, "Camera Offline", (190, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (60, 220, 220), 2)
        cv2.putText(frame, "Vision Memory Agent", (170, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 180, 180), 1)
        return frame


camera_service = CameraService()
