import time

from app.services.vision_touch.config import DEFAULT_CONFIG
from app.services.vision_touch.hand_tracker import HandTracker
from app.services.vision_touch import touch_state


class GestureEngine:
    def __init__(self) -> None:
        self._config = DEFAULT_CONFIG.copy()
        self._tracker = HandTracker()
        self._cursor = {"x": 0.5, "y": 0.5, "z": 0, "depth_level": "far"}
        self._state = touch_state.IDLE
        self._action = "none"
        self._gesture = "none"
        self._hand = None
        self._last_hand = None
        self._last_seen_hand = 0.0
        self._stable_since: float | None = None
        self._swipe_anchor_x = 0.5
        self._swipe_anchor_time = 0.0
        self._candidate_hits = 0
        self._hold_area = 0
        self._last_action_time = 0.0
        self._gesture_action = None
        self._last_click = 0.0
        self._click_count = 0
        self._stable_frames = 0
        self._fps = 0.0
        self._last_frame_time = 0.0
        self._latency_ms = 0

    def _update_gesture_state(self, now: float) -> None:
        x = self._cursor["x"]
        delta = x - self._swipe_anchor_x
        cooldown_ms = (now - self._last_action_time) * 1000
        elapsed = now - self._swipe_anchor_time
        if self._state not in {"HAND_READY", "SWIPE_LEFT", "SWIPE_RIGHT", "HOLD_LOCK", "FOCUS_DETAIL"}:
            self._state = "HAND_READY"
            self._gesture_action = None
            return
        if abs(delta) > 0.18 and 0.2 <= elapsed <= 1.2 and cooldown_ms >= 800:
            if delta < 0:
                self._state = "SWIPE_LEFT"
                self._gesture_action = "SWIPE_LEFT"
                self._action = "swipe_left"
            else:
                self._state = "SWIPE_RIGHT"
                self._gesture_action = "SWIPE_RIGHT"
                self._action = "swipe_right"
            self._last_action_time = now
            self._swipe_anchor_x = x
            self._swipe_anchor_time = now
            self._stable_since = now
            self._hold_area = self._hand["area"] if self._hand else self._hold_area
            return

        if abs(delta) > 0.07:
            self._stable_since = now
            self._state = "HAND_READY"
            self._action = "ready"
            self._gesture_action = None
            if elapsed > 1.2:
                self._swipe_anchor_x = x
                self._swipe_anchor_time = now
            return

        if self._stable_since is None:
            self._stable_since = now
        held_ms = (now - self._stable_since) * 1000
        area_change = abs((self._hand or {}).get("area", self._hold_area) - self._hold_area) / max(self._hold_area, 1)
        if held_ms >= 2000 and cooldown_ms >= 1000 and area_change < 0.35:
            self._state = "FOCUS_DETAIL"
            self._gesture_action = "FOCUS_DETAIL"
            self._action = "focus_detail"
            self._last_action_time = now
            self._stable_since = now
            self._hold_area = (self._hand or {}).get("area", self._hold_area)
        elif held_ms >= 1000 and cooldown_ms >= 1000 and area_change < 0.35:
            self._state = "HOLD_LOCK"
            self._gesture_action = "HOLD_LOCK"
            self._action = "hold_lock"
            self._last_action_time = now
            self._stable_since = now
            self._hold_area = (self._hand or {}).get("area", self._hold_area)
        else:
            self._state = "HAND_READY"
            self._action = "ready"
            self._gesture_action = None

    def _smooth_cursor(self, center: dict) -> None:
        alpha = self._config["smoothing_alpha"]
        self._cursor["x"] = round(alpha * center["x"] + (1 - alpha) * self._cursor["x"], 3)
        self._cursor["y"] = round(alpha * center["y"] + (1 - alpha) * self._cursor["y"], 3)

    def _depth_level(self, area: int) -> str:
        if area >= self._config["active_area_max"]:
            return "near"
        if area >= self._config["active_area_min"]:
            return "active"
        return "far"

    def update(self, frame, object_zones: list[dict] | None = None) -> None:
        self._object_zones = object_zones or []
        self._update_frame(frame)

    def _update_frame(self, frame) -> None:
        started = time.time()
        if not self._config["enabled"]:
            return
        now = time.time()
        if self._last_frame_time:
            self._fps = 1 / max(now - self._last_frame_time, 0.001)
        self._last_frame_time = now
        object_zones = getattr(self, "_object_zones", [])
        hand = self._tracker.detect(frame, self._config["tracking_mode"], self._config["active_area_min"], object_zones=object_zones)
        if not self._tracker.model_status()["hand_model_loaded"]:
            self._hand = None
            self._state = "DISABLED"
            self._action = "none"
            self._gesture = "none"
            self._gesture_action = None
            self._candidate_hits = 0
            self._stable_frames = 0
            self._cursor["depth_level"] = "far"
            self._latency_ms = int((time.time() - started) * 1000)
            return
        if hand is None:
            if self._state == "CANDIDATE":
                self._candidate_hits = 0
                self._state = touch_state.IDLE
                self._hand = None
                self._action = "none"
                self._gesture_action = None
            elif now - self._last_seen_hand < 0.5 and self._last_hand is not None and self._state in {"HAND_READY", "SWIPE_LEFT", "SWIPE_RIGHT", "HOLD_LOCK", "LOST"}:
                self._hand = self._last_hand
                self._state = "LOST"
                self._action = "none"
                self._gesture_action = None
            else:
                self._hand = None
                self._state = touch_state.IDLE
                self._action = "none"
                self._gesture = "none"
                self._stable_since = None
                self._candidate_hits = 0
                self._stable_frames = 0
                self._gesture_action = None
            self._cursor["depth_level"] = "far"
            self._latency_ms = int((time.time() - started) * 1000)
            return

        self._hand = hand
        self._last_seen_hand = now
        self._smooth_cursor(hand["center"])
        depth = self._depth_level(hand["area"])
        self._cursor["depth_level"] = depth
        self._cursor["z"] = {"far": 0, "active": 0.55, "near": 1}.get(depth, 0)
        self._gesture = "hand" if self._config["tracking_mode"] == "hand" else "marker"
        if self._state in {touch_state.IDLE, "CANDIDATE", "LOST"}:
            if self._is_same_candidate(hand):
                self._candidate_hits += 1
            else:
                self._candidate_hits = 1
            self._last_hand = hand
            if self._candidate_hits < 3:
                self._state = "CANDIDATE"
                self._action = "candidate"
                self._gesture_action = None
                self._stable_frames = self._candidate_hits
                self._latency_ms = int((time.time() - started) * 1000)
                return
            self._swipe_anchor_x = self._cursor["x"]
            self._swipe_anchor_time = now
            self._stable_since = now
            self._state = "HAND_READY"
            self._action = "ready"
            self._gesture_action = None
            self._stable_frames = self._candidate_hits
            self._hold_area = hand["area"]
            self._latency_ms = int((time.time() - started) * 1000)
            return
        self._last_hand = hand
        self._stable_frames += 1
        self._update_gesture_state(now)
        self._latency_ms = int((time.time() - started) * 1000)

    def _is_same_candidate(self, hand: dict) -> bool:
        if self._last_hand is None:
            return True
        cx, cy = hand["center"]["x"], hand["center"]["y"]
        px, py = self._last_hand["center"]["x"], self._last_hand["center"]["y"]
        return abs(cx - px) < 0.22 and abs(cy - py) < 0.22

    def get_status(self) -> dict:
        tracking = self._hand is not None
        hand_model_loaded = self._tracker.model_status()["hand_model_loaded"]
        hand_active = hand_model_loaded and (tracking or self._state == "LOST")
        hand_ready = hand_model_loaded and self._state in {"HAND_READY", "SWIPE_LEFT", "SWIPE_RIGHT", "HOLD_LOCK", "FOCUS_DETAIL"}
        reported_action = self._gesture_action if self._gesture_action and (time.time() - self._last_action_time) < 0.45 else None
        message = {
            "DISABLED": "手势模型未启用，当前使用键盘/鼠标交互",
            "HAND_READY": "手势已就绪，左右挥手切换记忆，停留 1 秒锁定",
            "CANDIDATE": "检测到疑似手，请保持手掌在画面侧边",
            "SWIPE_LEFT": "切换到上一条记忆",
            "SWIPE_RIGHT": "切换到下一条记忆",
            "HOLD_LOCK": "已锁定当前记忆",
            "FOCUS_DETAIL": "展开当前记忆详情",
            "LOST": "手势短暂丢失，保持就绪",
        }.get(self._state, "等待手势进入识别区域" if not tracking else "手势已就绪")
        return {
            "enabled": self._config["enabled"],
            "tracking": tracking,
            "tracking_mode": self._config["tracking_mode"],
            "state": self._state,
            "gesture": self._gesture,
            "action": self._action,
            "gesture_action": reported_action,
            "cursor": self._cursor.copy(),
            "hand": self._hand,
            "hand_active": hand_active,
            "hand_ready": hand_ready,
            "metrics": {
                "fps": round(self._fps, 1),
                "latency_ms": self._latency_ms,
                "stable_frames": self._stable_frames,
                "click_count": self._click_count,
            },
            "interaction": {
                "hand_active": hand_active,
                "hand_ready": hand_ready,
                "hand_state": self._state,
                "gesture_action": reported_action,
                "selected_memory_id": None,
                "locked_memory_id": None,
                "selected_label_zh": None,
                "locked_label_zh": None,
                "fps": round(self._fps, 1),
                "latency_ms": self._latency_ms,
                "stable_frames": self._stable_frames,
                "message": message,
                "debug": {
                    **self._tracker.get_debug(),
                    "candidate_hits": self._candidate_hits,
                },
            },
            "message": message,
        }

    def get_config(self) -> dict:
        return self._config.copy()

    def update_config(self, update: dict) -> dict:
        for key, value in update.items():
            if key in self._config and value is not None:
                self._config[key] = value
        return self.get_config()

    def reset_interaction(self) -> None:
        self._cursor = {"x": 0.5, "y": 0.5, "z": 0, "depth_level": "far"}
        self._state = touch_state.IDLE
        self._action = "none"
        self._gesture = "none"
        self._hand = None
        self._last_hand = None
        self._last_seen_hand = 0.0
        self._stable_since = None
        self._swipe_anchor_x = 0.5
        self._swipe_anchor_time = 0.0
        self._candidate_hits = 0
        self._hold_area = 0
        self._last_action_time = 0.0
        self._gesture_action = None
        self._stable_frames = 0


gesture_engine = GestureEngine()
