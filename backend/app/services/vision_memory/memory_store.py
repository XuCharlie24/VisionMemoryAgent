from datetime import datetime
from math import hypot

from app.services.vision_memory.config import DEDUP_WINDOW_SECONDS, MATCH_DISTANCE, MAX_OBJECTS


MIN_CONFIDENCE = 0.55
PERSON_MIN_CONFIDENCE = 0.65
PENDING_STABLE_SECONDS = 1.0
KNOWN_REQUIRED_HITS = 2
UNKNOWN_REQUIRED_HITS = 3
MAX_UNKNOWN_OBJECTS = 1
MAX_VISIBLE_OBJECTS = 10
MAX_PER_LABEL = 2

ADJACENT_POSITIONS = {
    "画面左上": {"画面左上", "画面上方", "画面左侧", "画面中央"},
    "画面上方": {"画面左上", "画面上方", "画面右上", "画面中央"},
    "画面右上": {"画面上方", "画面右上", "画面右侧", "画面中央"},
    "画面左侧": {"画面左上", "画面左侧", "画面左下", "画面中央"},
    "画面中央": {"画面左侧", "画面中央", "画面右侧", "画面上方", "画面下方"},
    "画面右侧": {"画面右上", "画面右侧", "画面右下", "画面中央"},
    "画面左下": {"画面左侧", "画面左下", "画面下方", "画面中央"},
    "画面下方": {"画面左下", "画面下方", "画面右下", "画面中央"},
    "画面右下": {"画面下方", "画面右下", "画面右侧", "画面中央"},
}


class MemoryStore:
    def __init__(self) -> None:
        self._objects: list[dict] = []
        self._pending: list[dict] = []
        self._next_id = 1

    def add_or_update_object(self, candidate: dict, hand_active: bool = False) -> tuple[dict | None, bool]:
        now_dt = datetime.now()
        now = now_dt.isoformat(timespec="seconds")
        if not self._can_consider(candidate, hand_active):
            return None, False
        match = self._find_match(candidate, now_dt)
        if match is None:
            pending = self._add_or_update_pending(candidate, now_dt)
            if not self._pending_ready(pending, now_dt):
                return None, False
            label = candidate.get("label", "unknown")
            label_zh = candidate.get("label_zh") or candidate.get("label_cn") or "未知物体"
            position = candidate.get("position") or candidate.get("position_hint") or "画面中央"
            if label == "unknown" and self._unknown_count() >= MAX_UNKNOWN_OBJECTS:
                return None, False
            if label != "unknown" and self._label_count(label_zh) >= MAX_PER_LABEL:
                oldest = self._oldest_label_object(label_zh)
                if oldest is not None:
                    self._objects.remove(oldest)
            obj = {
                "id": f"mem_{self._next_id:03d}",
                "object_id": f"{label}_{self._position_key(position)}",
                "label": label,
                "label_zh": label_zh,
                "label_cn": label_zh,
                "bbox": candidate["bbox"],
                "center": candidate.get("center"),
                "relative_position": candidate.get("relative_position"),
                "size_level": candidate.get("size_level"),
                "distance_hint": candidate.get("distance_hint"),
                "confidence": round(candidate["confidence"], 2),
                "first_seen": now,
                "last_seen": now,
                "seen_count": pending["hits"],
                "position": position,
                "position_hint": position,
                "source": candidate.get("source", "rule"),
            }
            self._next_id += 1
            self._objects.insert(0, obj)
            self._objects = self._objects[:MAX_OBJECTS]
            self._remove_pending(pending)
            return obj, True
        match["bbox"] = candidate["bbox"]
        match["center"] = candidate.get("center", match.get("center"))
        match["relative_position"] = candidate.get("relative_position", match.get("relative_position"))
        match["size_level"] = candidate.get("size_level", match.get("size_level"))
        match["distance_hint"] = candidate.get("distance_hint", match.get("distance_hint"))
        match["confidence"] = round(candidate["confidence"], 2)
        match["last_seen"] = now
        match["seen_count"] += 1
        match["label"] = candidate.get("label", match.get("label", "unknown"))
        match["label_zh"] = candidate.get("label_zh", match.get("label_zh", "未知物体"))
        match["label_cn"] = match["label_zh"]
        candidate_position = candidate.get("position") or candidate.get("position_hint") or match.get("position", "画面中央")
        current_position = match.get("position", "画面中央")
        if candidate_position != current_position:
            pending_position = match.get("_pending_position")
            pending_since = match.get("_pending_position_since")
            if pending_position != candidate_position:
                match["_pending_position"] = candidate_position
                match["_pending_position_since"] = now_dt.isoformat()
                candidate_position = current_position
            elif pending_since and (now_dt - datetime.fromisoformat(pending_since)).total_seconds() < 1.0:
                candidate_position = current_position
            else:
                match.pop("_pending_position", None)
                match.pop("_pending_position_since", None)
        else:
            match.pop("_pending_position", None)
            match.pop("_pending_position_since", None)
        match["position"] = candidate_position
        match["position_hint"] = match["position"]
        match["source"] = candidate.get("source", match.get("source", "rule"))
        match["object_id"] = f"{match['label']}_{self._position_key(match['position'])}"
        self._objects.remove(match)
        self._objects.insert(0, match)
        return match, False

    def _can_consider(self, candidate: dict, hand_active: bool) -> bool:
        label = candidate.get("label", "unknown")
        confidence = float(candidate.get("confidence", 0))
        if candidate.get("source") != "model":
            return False
        if label == "unknown":
            return False
        if candidate.get("is_hand") or candidate.get("is_hand_like"):
            return False
        if candidate.get("is_background"):
            return False
        if confidence < MIN_CONFIDENCE:
            return False
        if label == "person" and confidence < PERSON_MIN_CONFIDENCE:
            return False
        if hand_active and label == "unknown":
            return False
        return True

    def _add_or_update_pending(self, candidate: dict, now: datetime) -> dict:
        match = self._find_pending(candidate)
        if match is None:
            match = {
                "label_zh": candidate.get("label_zh") or candidate.get("label_cn") or "未知物体",
                "label": candidate.get("label", "unknown"),
                "bbox": candidate["bbox"],
                "position": candidate.get("position") or candidate.get("position_hint") or "画面中央",
                "confidence": candidate.get("confidence", 0),
                "first_seen_dt": now,
                "last_seen_dt": now,
                "hits": 1,
            }
            self._pending.append(match)
            self._pending = self._pending[-12:]
            return match
        match["bbox"] = candidate["bbox"]
        match["position"] = candidate.get("position") or candidate.get("position_hint") or match["position"]
        match["confidence"] = candidate.get("confidence", match["confidence"])
        match["last_seen_dt"] = now
        match["hits"] += 1
        return match

    def _pending_ready(self, pending: dict, now: datetime) -> bool:
        required_hits = UNKNOWN_REQUIRED_HITS if pending.get("label") == "unknown" else KNOWN_REQUIRED_HITS
        stable_seconds = (now - pending["first_seen_dt"]).total_seconds()
        return pending["hits"] >= required_hits or (pending.get("label") != "unknown" and stable_seconds >= PENDING_STABLE_SECONDS)

    def _find_pending(self, candidate: dict) -> dict | None:
        cx, cy = self._center(candidate["bbox"])
        label_zh = candidate.get("label_zh") or candidate.get("label_cn") or "未知物体"
        for item in self._pending:
            if item.get("label_zh") != label_zh:
                continue
            ox, oy = self._center(item["bbox"])
            if hypot(cx - ox, cy - oy) < MATCH_DISTANCE:
                return item
        return None

    def _remove_pending(self, pending: dict) -> None:
        self._pending = [item for item in self._pending if item is not pending]

    def _find_match(self, candidate: dict, now: datetime) -> dict | None:
        cx, cy = self._center(candidate["bbox"])
        label_zh = candidate.get("label_zh") or candidate.get("label_cn") or "未知物体"
        position = candidate.get("position") or candidate.get("position_hint") or "画面中央"
        for obj in self._objects:
            if obj.get("label_zh") != label_zh:
                continue
            if not self._positions_close(obj.get("position") or obj.get("position_hint"), position):
                continue
            if (now - datetime.fromisoformat(obj["last_seen"])).total_seconds() > DEDUP_WINDOW_SECONDS:
                continue
            ox, oy = self._center(obj["bbox"])
            if hypot(cx - ox, cy - oy) < MATCH_DISTANCE:
                return obj
        return None

    def _center(self, bbox: list[int]) -> tuple[float, float]:
        x, y, w, h = bbox
        return x + w / 2, y + h / 2

    def reset(self) -> None:
        self._objects = []
        self._pending = []
        self._next_id = 1

    def get_snapshot(self) -> list[dict]:
        known = [obj for obj in self._objects if obj.get("label") != "unknown"]
        unknown = [obj for obj in self._objects if obj.get("label") == "unknown"]
        visible = (known + unknown)[:MAX_VISIBLE_OBJECTS]
        return [{key: value for key, value in obj.items() if not key.startswith("_")} for obj in visible]

    def get_pending_count(self) -> int:
        return len(self._pending)

    def _unknown_count(self) -> int:
        return sum(1 for obj in self._objects if obj.get("label") == "unknown")

    def _label_count(self, label_zh: str) -> int:
        return sum(1 for obj in self._objects if obj.get("label_zh") == label_zh)

    def _oldest_label_object(self, label_zh: str) -> dict | None:
        candidates = [obj for obj in self._objects if obj.get("label_zh") == label_zh]
        if not candidates:
            return None
        return min(candidates, key=lambda obj: obj.get("last_seen", ""))

    def _positions_close(self, left: str | None, right: str | None) -> bool:
        if not left or not right:
            return False
        return right in ADJACENT_POSITIONS.get(left, {left})

    def _position_key(self, position: str) -> str:
        return {
            "画面左侧": "left",
            "画面中央": "center",
            "画面右侧": "right",
            "画面上方": "top",
            "画面下方": "bottom",
            "画面左上": "left_upper",
            "画面右上": "right_upper",
            "画面左下": "left_lower",
            "画面右下": "right_lower",
        }.get(position, "center")
