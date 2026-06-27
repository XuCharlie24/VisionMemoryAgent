import cv2
import numpy as np
from pathlib import Path

from app.services.vision_touch.config import COLOR_MARKER_HSV_RANGES


class HandTracker:
    def __init__(self) -> None:
        backend_dir = Path(__file__).resolve().parents[3]
        self._hand_model_paths = [
            backend_dir / "models" / "palm_detection.onnx",
            backend_dir / "models" / "hand_detector.onnx",
            backend_dir / "models" / "hand_landmark.onnx",
        ]
        self._hand_model_path = next((path for path in self._hand_model_paths if path.exists()), None)
        self._last_debug = {
            "hand_source": "none",
            "hand_score": 0,
            "hand_confidence": 0,
            "hand_model_loaded": self._hand_model_path is not None,
            "hand_model_name": self._hand_model_path.name if self._hand_model_path else None,
            "candidate_count": 0,
            "valid_hand": False,
            "reject_reason": "hand_model_missing" if self._hand_model_path is None else None,
            "face_excluded": False,
            "object_excluded": False,
            "skin_ratio": 0,
            "bbox_area_ratio": 0,
        }

    def detect(self, frame, mode: str, active_area_min: int, object_zones: list[dict] | None = None) -> dict | None:
        if self._hand_model_path is None:
            self._last_debug.update({
                "hand_source": "none",
                "hand_score": 0,
                "hand_confidence": 0,
                "hand_model_loaded": False,
                "hand_model_name": None,
                "candidate_count": 0,
                "valid_hand": False,
                "reject_reason": "hand_model_missing",
            })
            return None
        if mode == "color_marker":
            return self._detect_color_marker(frame, active_area_min)
        return self._detect_hand(frame, active_area_min, object_zones or [])

    def model_status(self) -> dict:
        return {
            "hand_model_loaded": self._hand_model_path is not None,
            "hand_model_name": self._hand_model_path.name if self._hand_model_path else None,
        }

    def _detect_hand(self, frame, active_area_min: int, object_zones: list[dict]) -> dict | None:
        small, scale_x, scale_y = self._small_frame(frame)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
        lower = np.array([0, 25, 55], dtype=np.uint8)
        upper = np.array([25, 190, 255], dtype=np.uint8)
        hsv_mask = cv2.inRange(hsv, lower, upper)
        ycrcb_mask = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))
        mask = cv2.bitwise_or(hsv_mask, ycrcb_mask)
        mask = cv2.medianBlur(mask, 5)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), dtype=np.uint8), iterations=1)
        small_head_zone = self._detect_head_zone(mask, small.shape)
        head_zone = self._scale_bbox(small_head_zone, scale_x, scale_y) if small_head_zone is not None else None
        roi_mask = self._entry_roi_mask(mask.shape)
        candidate_mask = cv2.bitwise_and(mask, roi_mask)
        hand = self._best_hand_candidate(candidate_mask, mask, small, frame.shape, scale_x, scale_y, object_zones, head_zone)
        if hand is not None:
            hand["roi"] = "entry"
            return hand
        return None

    def _detect_color_marker(self, frame, active_area_min: int) -> dict | None:
        small, scale_x, scale_y = self._small_frame(frame)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        mask = np.zeros(small.shape[:2], dtype=np.uint8)
        for ranges in COLOR_MARKER_HSV_RANGES.values():
            for lower, upper in ranges:
                mask |= cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
        mask = cv2.medianBlur(mask, 5)
        return self._largest_region(mask, small, max(250, active_area_min // 18), "color_marker", scale_x, scale_y, frame.shape)

    def _small_frame(self, frame):
        target_width = 320
        scale = target_width / frame.shape[1]
        target_height = int(frame.shape[0] * scale)
        small = cv2.resize(frame, (target_width, target_height))
        return small, frame.shape[1] / target_width, frame.shape[0] / target_height

    def _best_hand_candidate(self, candidate_mask, skin_mask, frame, original_shape, scale_x: float, scale_y: float, object_zones: list[dict], head_zone: list[int] | None) -> dict | None:
        contours, _ = cv2.findContours(candidate_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:6]
        self._last_debug = {
            "candidate_count": len(contours),
            "valid_hand": False,
            "reject_reason": "no_candidate" if not contours else None,
            "face_excluded": head_zone is not None,
            "object_excluded": False,
            "skin_ratio": 0,
            "bbox_area_ratio": 0,
        }
        best = None
        best_score = -1
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            bbox = [int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y)]
            reason, features = self._reject_reason(bbox, skin_mask, frame.shape, original_shape, object_zones, head_zone)
            self._last_debug.update({
                "reject_reason": reason,
                "hand_source": "rule",
                "hand_score": round(features.get("hand_score", 0), 2),
                "skin_ratio": round(features["skin_ratio"], 2),
                "bbox_area_ratio": round(features["area_ratio"], 3),
                "aspect_ratio": round(features["aspect"], 2),
                "object_excluded": reason == "overlap_object",
            })
            if reason is not None:
                continue
            score = features["hand_score"]
            if score > best_score:
                best_score = score
                area = cv2.contourArea(contour) * scale_x * scale_y
                best = {
                    "mode": "hand",
                    "bbox": bbox,
                    "center": {"x": (bbox[0] + bbox[2] / 2) / original_shape[1], "y": (bbox[1] + bbox[3] / 2) / original_shape[0]},
                    "area": int(area),
                    "confidence": round(min(0.96, 0.58 + features["skin_ratio"] * 0.28 + min(features["area_ratio"] * 2, 0.12)), 2),
                    "skin_ratio": round(features["skin_ratio"], 2),
                    "area_ratio": round(features["area_ratio"], 3),
                    "hand_score": round(features["hand_score"], 2),
                }
        if best is not None:
            self._last_debug.update({"valid_hand": True, "reject_reason": None, "hand_source": "rule", "hand_score": best["hand_score"]})
        return best

    def _reject_reason(self, bbox: list[int], skin_mask, small_shape, original_shape, object_zones: list[dict], head_zone: list[int] | None) -> tuple[str | None, dict]:
        x, y, w, h = bbox
        area_ratio = (w * h) / max(original_shape[0] * original_shape[1], 1)
        aspect = w / max(h, 1)
        cx = x + w / 2
        cy = y + h / 2
        sx = int(x / (original_shape[1] / small_shape[1]))
        sy = int(y / (original_shape[0] / small_shape[0]))
        sw = max(1, int(w / (original_shape[1] / small_shape[1])))
        sh = max(1, int(h / (original_shape[0] / small_shape[0])))
        roi = skin_mask[max(sy, 0):min(sy + sh, skin_mask.shape[0]), max(sx, 0):min(sx + sw, skin_mask.shape[1])]
        skin_ratio = float(np.mean(roi > 0)) if roi.size else 0.0
        contour_like = self._contour_hand_score(bbox, skin_mask, small_shape, original_shape)
        features = {"area_ratio": area_ratio, "aspect": aspect, "skin_ratio": skin_ratio, "contour_like": contour_like, "hand_score": 0}
        if not self._in_entry_zone(cx / original_shape[1], cy / original_shape[0]):
            return "outside_entry_zone", features
        if area_ratio < 0.005:
            return "area_too_small", features
        if area_ratio > 0.18:
            return "area_too_large", features
        if aspect < 0.35 or aspect > 2.8:
            return "bad_aspect", features
        if skin_ratio < 0.18:
            features["hand_score"] = self._hand_score(features)
            return "skin_ratio_low", features
        if head_zone is not None and (self._point_in_bbox(cx, cy, head_zone) or self._iou(bbox, head_zone) > 0.15 or area_ratio > self._area_ratio(head_zone, original_shape) * 0.85):
            return "in_face_zone", features
        for zone in object_zones:
            obj_bbox = zone.get("bbox")
            label = zone.get("label")
            if not obj_bbox or label in {"person", "unknown"}:
                continue
            if self._point_in_bbox(cx, cy, obj_bbox) or self._iou(bbox, obj_bbox) > 0.25:
                return "overlap_object", features
        features["hand_score"] = self._hand_score(features)
        if contour_like < 0.06 and aspect > 1.9:
            return "contour_not_hand_like", features
        if features["hand_score"] < 0.70:
            return "score_too_low", features
        return None, features

    def _hand_score(self, features: dict) -> float:
        score = 0.0
        if features["skin_ratio"] >= 0.18:
            score += 0.25
        if 0.005 <= features["area_ratio"] <= 0.18:
            score += 0.20
        if 0.35 <= features["aspect"] <= 2.8:
            score += 0.15
        score += min(0.15, features.get("contour_like", 0))
        score += 0.15
        score += 0.10
        if features["skin_ratio"] < 0.18:
            score -= 0.15
        return max(0.0, min(1.0, score))

    def _contour_hand_score(self, bbox: list[int], skin_mask, small_shape, original_shape) -> float:
        x, y, w, h = bbox
        sx_scale = original_shape[1] / small_shape[1]
        sy_scale = original_shape[0] / small_shape[0]
        sx, sy = int(x / sx_scale), int(y / sy_scale)
        sw, sh = max(1, int(w / sx_scale)), max(1, int(h / sy_scale))
        roi = skin_mask[max(sy, 0):min(sy + sh, skin_mask.shape[0]), max(sx, 0):min(sx + sw, skin_mask.shape[1])]
        if roi.size == 0:
            return 0.0
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0.0
        contour = max(contours, key=cv2.contourArea)
        area = max(cv2.contourArea(contour), 1)
        perimeter = cv2.arcLength(contour, True)
        hull = cv2.convexHull(contour)
        hull_area = max(cv2.contourArea(hull), 1)
        solidity = area / hull_area
        complexity = min(1.0, perimeter / max(np.sqrt(area), 1) / 18)
        return max(0.0, min(0.15, (1 - abs(solidity - 0.72)) * 0.08 + complexity * 0.07))

    def _largest_region(self, mask, frame, min_area: int, mode: str, scale_x: float, scale_y: float, original_shape) -> dict | None:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        if area < min_area:
            return None
        x, y, w, h = cv2.boundingRect(contour)
        ox, oy, ow, oh = int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y)
        return {
            "mode": mode,
            "bbox": [ox, oy, ow, oh],
            "center": {"x": (ox + ow / 2) / original_shape[1], "y": (oy + oh / 2) / original_shape[0]},
            "area": int(area * scale_x * scale_y),
            "confidence": round(min(0.96, 0.55 + area / 18000), 2),
        }

    def _entry_roi_mask(self, shape) -> np.ndarray:
        height, width = shape
        mask = np.zeros(shape, dtype=np.uint8)
        mask[:, : int(width * 0.35)] = 255
        mask[:, int(width * 0.65):] = 255
        mask[int(height * 0.55):, :] = 255
        return mask

    def _in_entry_zone(self, x: float, y: float) -> bool:
        if x <= 0.35 or x >= 0.65 or y >= 0.55:
            if not (0.25 <= x <= 0.75 and y <= 0.55):
                return True
        return False

    def _detect_head_zone(self, skin_mask, shape) -> list[int] | None:
        height, width = shape[:2]
        central_upper = np.zeros_like(skin_mask)
        central_upper[: int(height * 0.58), int(width * 0.25): int(width * 0.75)] = 255
        mask = cv2.bitwise_and(skin_mask, central_upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return [int(width * 0.25), 0, int(width * 0.5), int(height * 0.55)]
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        if area < width * height * 0.015:
            return [int(width * 0.25), 0, int(width * 0.5), int(height * 0.55)]
        x, y, w, h = cv2.boundingRect(contour)
        expand_x = int(w * 0.4)
        expand_y = int(h * 0.6)
        return [
            max(0, x - expand_x),
            max(0, y - expand_y),
            min(width - max(0, x - expand_x), w + expand_x * 2),
            min(height - max(0, y - expand_y), h + expand_y * 2),
        ]

    def _point_in_bbox(self, x: float, y: float, bbox: list[int]) -> bool:
        bx, by, bw, bh = bbox
        return bx <= x <= bx + bw and by <= y <= by + bh

    def _iou(self, a: list[int], b: list[int]) -> float:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        x1, y1 = max(ax, bx), max(ay, by)
        x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        return inter / max(aw * ah + bw * bh - inter, 1)

    def _area_ratio(self, bbox: list[int], shape) -> float:
        return (bbox[2] * bbox[3]) / max(shape[0] * shape[1], 1)

    def _scale_bbox(self, bbox: list[int], scale_x: float, scale_y: float) -> list[int]:
        x, y, w, h = bbox
        return [int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y)]

    def get_debug(self) -> dict:
        return self._last_debug.copy()
