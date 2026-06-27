from pathlib import Path

import cv2
import numpy as np

from app.services.vision_memory.config import BACKGROUND_LEARNING_RATE, MIN_CONTOUR_AREA


LABELS_ZH = {
    "person": "人",
    "cell phone": "手机",
    "phone": "手机",
    "cup": "水杯",
    "book": "书本",
    "mouse": "鼠标",
    "keyboard": "键盘",
    "bottle": "瓶子",
    "laptop": "笔记本电脑",
    "tv": "显示器",
    "monitor": "显示器",
    "backpack": "背包",
    "handbag": "包",
    "bag": "包",
    "clock": "时钟",
    "remote": "遥控器",
    "teddy bear": "玩偶",
    "scissors": "剪刀",
    "sports ball": "球",
    "apple": "苹果",
    "banana": "香蕉",
    "orange": "橙子",
    "potted plant": "盆栽",
    "vase": "花瓶",
    "chair": "椅子",
    "computer": "电脑",
    "toy": "玩偶",
    "unknown": "未知物体",
}

COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
    "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]

ALLOWED_MODEL_LABELS = {
    "person",
    "cup",
    "bottle",
    "cell phone",
    "book",
    "mouse",
    "keyboard",
    "laptop",
    "chair",
    "backpack",
    "handbag",
    "remote",
    "teddy bear",
    "potted plant",
    "vase",
    "apple",
    "banana",
    "orange",
}

DISPLAY_CONF_THRESHOLD = 0.45
NMS_IOU_THRESHOLD = 0.45
MAX_DETECTIONS = 6


class ModelDetector:
    def __init__(self) -> None:
        backend_dir = Path(__file__).resolve().parents[3]
        self._model_paths = [
            backend_dir / "models" / "yolov5n.onnx",
            backend_dir / "models" / "yolov8n.onnx",
            backend_dir / "models" / "nanodet.onnx",
            backend_dir / "models" / "mobilenet_ssd.onnx",
        ]
        self._net = None
        self._model_name = "yolov5n_coco_320"
        self._requested_input_size = 320
        self._fallback_input_size = 640
        self._input_size = self._requested_input_size
        self._input_fallback_reason = None
        self._model_path = None
        self._load()

    def _load(self) -> None:
        for path in self._model_paths:
            if not path.exists():
                continue
            try:
                self._net = cv2.dnn.readNetFromONNX(str(path))
                self._model_path = str(path)
                return
            except Exception:
                self._net = None
                self._model_path = None

    def available(self) -> bool:
        return self._net is not None

    def model_path(self) -> str | None:
        return self._model_path

    def model_name(self) -> str | None:
        return self._model_name if self._net is not None else None

    def input_size(self) -> int:
        return self._input_size

    def requested_input_size(self) -> int:
        return self._requested_input_size

    def input_fallback_reason(self) -> str | None:
        return self._input_fallback_reason

    def detect(self, frame) -> list[dict]:
        if self._net is None:
            return []
        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (self._input_size, self._input_size), swapRB=True, crop=False)
        self._net.setInput(blob)
        try:
            outputs = self._net.forward()
        except cv2.error:
            if self._input_size != self._fallback_input_size:
                self._input_size = self._fallback_input_size
                self._input_fallback_reason = "model_static_640"
                return self.detect(frame)
            raise
        rows = self._normalize_outputs(outputs)
        boxes, scores, class_ids = [], [], []
        for row in rows:
            if len(row) < 6:
                continue
            if len(row) == 84:
                objectness = 1.0
                class_scores = row[4:]
            else:
                objectness = float(row[4]) if len(row) > 6 else 1.0
                class_scores = row[5:] if len(row) > 6 else row[4:]
            class_id = int(np.argmax(class_scores))
            confidence = objectness * float(class_scores[class_id])
            label = COCO_LABELS[class_id] if class_id < len(COCO_LABELS) else "unknown"
            if label not in ALLOWED_MODEL_LABELS or confidence < DISPLAY_CONF_THRESHOLD:
                continue
            cx, cy, bw, bh = [float(v) for v in row[:4]]
            x = int((cx - bw / 2) * width / self._input_size)
            y = int((cy - bh / 2) * height / self._input_size)
            w = int(bw * width / self._input_size)
            h = int(bh * height / self._input_size)
            if w * h < width * height * 0.003:
                continue
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
            w = max(1, min(width - x, w))
            h = max(1, min(height - y, h))
            boxes.append([x, y, w, h])
            scores.append(float(confidence))
            class_ids.append(class_id)
        indices = cv2.dnn.NMSBoxes(boxes, scores, DISPLAY_CONF_THRESHOLD, NMS_IOU_THRESHOLD)
        if len(indices) == 0:
            return []
        result = []
        for index in np.array(indices).flatten()[:MAX_DETECTIONS]:
            label = COCO_LABELS[class_ids[index]] if class_ids[index] < len(COCO_LABELS) else "unknown"
            result.append({"bbox": boxes[index], "label": label, "confidence": round(scores[index], 2), "source": "model"})
        return result

    def _normalize_outputs(self, outputs):
        output = outputs[0] if isinstance(outputs, tuple) else outputs
        output = np.squeeze(output)
        if output.ndim == 1:
            output = np.expand_dims(output, 0)
        if output.shape[0] < output.shape[-1] and output.shape[0] in {84, 85}:
            output = output.T
        return output


class ObjectTracker:
    def __init__(self) -> None:
        self._background = None
        self._last_profile = {}
        self._model = ModelDetector()
        self._allow_rule_fallback = False

    def process_frame(self, frame, hand_active: bool = False) -> list[dict]:
        started = cv2.getTickCount()
        if not self._model.available():
            self._profile(started, cv2.getTickCount(), cv2.getTickCount(), 0, 0, source="model_missing")
            return []
        model_candidates = self._model_candidates(frame, hand_active)
        self._profile(started, cv2.getTickCount(), cv2.getTickCount(), 0, len(model_candidates), source="model")
        if model_candidates or not self._allow_rule_fallback:
            return model_candidates
        small = cv2.resize(frame, (320, 240))
        resized_at = cv2.getTickCount()
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        if self._background is None:
            self._background = gray.astype("float")
            self._profile(started, resized_at, cv2.getTickCount(), 0, 0)
            return []
        cv2.accumulateWeighted(gray, self._background, BACKGROUND_LEARNING_RATE)
        diff = cv2.absdiff(gray, cv2.convertScaleAbs(self._background))
        _, thresh = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected_at = cv2.getTickCount()
        candidates = []
        scale_x = frame.shape[1] / 320
        scale_y = frame.shape[0] / 240
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MIN_CONTOUR_AREA / 4:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            bbox = [int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y)]
            if self._is_edge_noise(bbox, frame.shape[1], frame.shape[0]):
                continue
            if hand_active and self._skin_ratio(frame, bbox) > 0.18:
                continue
            label, confidence_boost = self._classify_by_rule(frame, bbox)
            confidence = self._confidence(area, confidence_boost, label)
            position_meta = self._position_meta(bbox, frame.shape[1], frame.shape[0])
            candidates.append({
                "bbox": bbox,
                "center": position_meta["center"],
                "label": label,
                "label_zh": LABELS_ZH[label],
                "label_cn": LABELS_ZH[label],
                "confidence": confidence,
                "position": position_meta["position"],
                "position_hint": position_meta["position"],
                "relative_position": position_meta["relative_position"],
                "size_level": position_meta["size_level"],
                "distance_hint": position_meta["distance_hint"],
                "is_background": self._is_background_like(frame, bbox, label),
                "is_hand": self._skin_ratio(frame, bbox) > 0.30,
                "is_hand_like": self._skin_ratio(frame, bbox) > 0.24,
                "source": "rule",
            })
        classified = [item for item in candidates if not item["is_background"] and not item["is_hand_like"]]
        self._profile(started, resized_at, detected_at, len(contours), len(classified), source="rule")
        return sorted(classified, key=lambda item: (item["label"] == "unknown", -item["confidence"], -(item["bbox"][2] * item["bbox"][3])))[:4]

    def _model_candidates(self, frame, hand_active: bool) -> list[dict]:
        detections = self._model.detect(frame)
        candidates = []
        for detection in detections:
            bbox = detection["bbox"]
            label = self._normalize_label(detection["label"])
            if label == "unknown" and detection["confidence"] < 0.65:
                continue
            if hand_active and self._skin_ratio(frame, bbox) > 0.18 and label not in {"cell phone", "phone"}:
                continue
            position_meta = self._position_meta(bbox, frame.shape[1], frame.shape[0])
            candidates.append({
                "bbox": bbox,
                "center": position_meta["center"],
                "label": label,
                "label_zh": LABELS_ZH.get(label, LABELS_ZH.get(detection["label"], "未知物体")),
                "label_cn": LABELS_ZH.get(label, LABELS_ZH.get(detection["label"], "未知物体")),
                "confidence": detection["confidence"],
                "position": position_meta["position"],
                "position_hint": position_meta["position"],
                "relative_position": position_meta["relative_position"],
                "size_level": position_meta["size_level"],
                "distance_hint": position_meta["distance_hint"],
                "is_background": False,
                "is_hand": False,
                "is_hand_like": False,
                "source": "model",
            })
        return candidates

    def _normalize_label(self, label: str) -> str:
        if label == "cell phone":
            return "phone"
        if label == "tv":
            return "monitor"
        if label == "teddy bear":
            return "toy"
        if label == "handbag":
            return "bag"
        return label if label in LABELS_ZH else "unknown"

    def _classify_by_rule(self, frame, bbox: list[int]) -> tuple[str, float]:
        x, y, w, h = bbox
        height, width = frame.shape[:2]
        x1, y1 = max(x, 0), max(y, 0)
        x2, y2 = min(x + w, width), min(y + h, height)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return "unknown", 0.0

        area_ratio = (w * h) / max(width * height, 1)
        aspect = w / max(h, 1)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_v = float(np.mean(hsv[:, :, 2]))
        mean_s = float(np.mean(hsv[:, :, 1]))
        dark_ratio = float(np.mean(gray < 80))
        bright_ratio = float(np.mean(gray > 175))
        edges = cv2.Canny(gray, 60, 140)
        edge_ratio = float(np.mean(edges > 0))
        circularity = self._circularity(gray)

        if h > height * 0.45 and 0.28 <= aspect <= 0.9 and area_ratio > 0.08:
            return "person", 0.18
        if area_ratio > 0.06 and aspect > 1.35 and edge_ratio > 0.025:
            return "book", 0.16
        if 0.012 <= area_ratio <= 0.16 and 0.32 <= aspect <= 0.82 and dark_ratio > 0.26 and edge_ratio > 0.018:
            return "phone", 0.20
        if 0.012 <= area_ratio <= 0.14 and 0.45 <= aspect <= 1.25 and mean_v > 90 and (mean_s < 155 or bright_ratio > 0.24 or circularity > 0.18):
            return "cup", 0.18
        if 0.008 <= area_ratio <= 0.06 and 0.75 <= aspect <= 1.8 and dark_ratio > 0.30:
            return "mouse", 0.15
        if area_ratio > 0.08 and 2.0 <= aspect <= 5.5 and dark_ratio > 0.25:
            return "keyboard", 0.10
        if 0.025 <= area_ratio <= 0.12 and 0.28 <= aspect <= 0.75 and mean_v > 90:
            return "bottle", 0.10
        if 0.015 <= area_ratio <= 0.16 and mean_s > 90 and edge_ratio > 0.02:
            return "toy", 0.08
        return "unknown", 0.0

    def _confidence(self, area: float, boost: float, label: str) -> float:
        base = 0.50 + min(0.16, area / 28000)
        if label == "unknown":
            return round(min(0.62, base - 0.05), 2)
        return round(min(0.85, max(0.55, base + boost)), 2)

    def _skin_ratio(self, frame, bbox: list[int]) -> float:
        x, y, w, h = bbox
        roi = frame[max(y, 0):min(y + h, frame.shape[0]), max(x, 0):min(x + w, frame.shape[1])]
        if roi.size == 0:
            return 0.0
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 25, 55], dtype=np.uint8), np.array([25, 190, 255], dtype=np.uint8))
        return float(np.mean(mask > 0))

    def _is_edge_noise(self, bbox: list[int], width: int, height: int) -> bool:
        x, y, w, h = bbox
        area_ratio = (w * h) / max(width * height, 1)
        touches_edge = x <= 4 or y <= 4 or x + w >= width - 4 or y + h >= height - 4
        return touches_edge and area_ratio < 0.025

    def _is_background_like(self, frame, bbox: list[int], label: str) -> bool:
        if label != "unknown":
            return False
        x, y, w, h = bbox
        area_ratio = (w * h) / max(frame.shape[0] * frame.shape[1], 1)
        if area_ratio > 0.32:
            return True
        roi = frame[max(y, 0):min(y + h, frame.shape[0]), max(x, 0):min(x + w, frame.shape[1])]
        if roi.size == 0:
            return True
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        return float(np.std(gray)) < 12 and area_ratio > 0.05

    def _circularity(self, gray) -> float:
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0.0
        contour = max(contours, key=cv2.contourArea)
        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            return 0.0
        return float(4 * np.pi * cv2.contourArea(contour) / (perimeter * perimeter))

    def _profile(self, started, resized_at, detected_at, contour_count: int, candidate_count: int, source: str = "rule") -> None:
        freq = cv2.getTickFrequency()
        finished = cv2.getTickCount()
        self._last_profile = {
            "resize_ms": round((resized_at - started) * 1000 / freq, 1),
            "detect_ms": round((detected_at - resized_at) * 1000 / freq, 1),
            "classify_ms": round((finished - detected_at) * 1000 / freq, 1),
            "contours": contour_count,
            "candidates": candidate_count,
            "source": source,
            "model_available": self._model.available(),
            "model_name": self._model.model_name(),
            "model_path": self._model.model_path(),
            "model_input_size": self._model.input_size(),
            "model_requested_input_size": self._model.requested_input_size(),
            "model_input_fallback_reason": self._model.input_fallback_reason(),
            "rule_fallback_enabled": self._allow_rule_fallback,
        }

    def detector_status(self) -> dict:
        model_loaded = self._model.available()
        model_name = self._model.model_name()
        model_path = self._model.model_path()
        input_size = self._model.input_size()
        return {
            "model_loaded": model_loaded,
            "model_name": model_name,
            "model_path": model_path,
            "backend": "opencv_dnn",
            "input_size": input_size,
            "class_count": len(COCO_LABELS),
            "object_model_loaded": model_loaded,
            "object_model_name": model_name,
            "object_model_path": model_path,
            "object_model_input_size": input_size,
            "object_model_requested_input_size": self._model.requested_input_size(),
            "object_model_input_fallback_reason": self._model.input_fallback_reason(),
            "inference_backend": "opencv_dnn",
            "coco_classes": len(COCO_LABELS),
            "is_coco": True,
            "nms_enabled": True,
            "display_conf_threshold": DISPLAY_CONF_THRESHOLD,
            "nms_iou": NMS_IOU_THRESHOLD,
            "max_detections": MAX_DETECTIONS,
            "rule_fallback_enabled": self._allow_rule_fallback,
        }

    def get_profile(self) -> dict:
        return self._last_profile.copy()

    def _position_hint(self, bbox: list[int], width: int, height: int) -> str:
        return self._position_meta(bbox, width, height)["position"]

    def _position_meta(self, bbox: list[int], width: int, height: int) -> dict:
        x, y, w, h = bbox
        cx = x + w / 2
        cy = y + h / 2
        rx = round(cx / max(width, 1), 3)
        ry = round(cy / max(height, 1), 3)
        col = "left" if rx < 0.33 else "right" if rx > 0.67 else "center"
        row = "upper" if ry < 0.33 else "lower" if ry > 0.67 else "middle"
        names = {
            ("left", "upper"): "画面左上",
            ("center", "upper"): "画面上方",
            ("right", "upper"): "画面右上",
            ("left", "middle"): "画面左侧",
            ("center", "middle"): "画面中央",
            ("right", "middle"): "画面右侧",
            ("left", "lower"): "画面左下",
            ("center", "lower"): "画面下方",
            ("right", "lower"): "画面右下",
        }
        area_ratio = (w * h) / max(width * height, 1)
        size_level = "small" if area_ratio < 0.04 else "large" if area_ratio > 0.16 else "medium"
        distance_hint = "near" if area_ratio > 0.12 else "far" if area_ratio < 0.025 else "middle"
        return {
            "position": names[(col, row)],
            "center": [int(cx), int(cy)],
            "relative_position": {"x": rx, "y": ry, "zone": f"{col}_{row}"},
            "size_level": size_level,
            "distance_hint": distance_hint,
        }
