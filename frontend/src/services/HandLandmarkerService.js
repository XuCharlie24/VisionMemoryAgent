import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";
import { API_BASE } from "./rdkApi";

export const HAND_MODEL_PATH = "/models/hand_landmarker.task";
export const HAND_WASM_PATH = "/vendor/mediapipe/tasks-vision/wasm";
export const HAND_FRAME_INTERVAL_MS = 190;
export const HAND_STATUS_THROTTLE_MS = 500;

const PALM_POINTS = [0, 5, 9, 13, 17];
const READY_STREAK = 2;
const SWIPE_THRESHOLD = 0.18;
const EMPTY_CURSOR = { x: 0.5, y: 0.5, z: 0, depth_level: "far" };
const EMPTY_METRICS = { fps: 0, latency_ms: 0, stable_frames: 0, click_count: 0 };

function compactError(error) {
  const message = String(error?.message || error || "unknown error");
  if (/404|not found/i.test(message)) return "hand_landmarker.task missing";
  return message.replace(/\s+/g, " ").slice(0, 180);
}

async function assertModelExists() {
  const response = await fetch(HAND_MODEL_PATH, { method: "HEAD", cache: "no-store" });
  if (!response.ok) throw new Error("hand_landmarker.task missing");
}

function averagePalm(landmarks) {
  const center = PALM_POINTS.reduce(
    (acc, index) => {
      acc.x += landmarks[index].x;
      acc.y += landmarks[index].y;
      acc.z += landmarks[index].z || 0;
      return acc;
    },
    { x: 0, y: 0, z: 0 },
  );
  return {
    rawX: center.x / PALM_POINTS.length,
    x: 1 - center.x / PALM_POINTS.length,
    y: center.y / PALM_POINTS.length,
    z: center.z / PALM_POINTS.length,
  };
}

function handScore(result) {
  return result.handedness?.[0]?.[0]?.score ?? 0.8;
}

function createStatus({ state, message, center = null, confidence = 0, landmarksCount = 0, metrics = EMPTY_METRICS, error = null, action = "none", snapshot = "idle" }) {
  const handReady = ["HAND_READY", "SWIPE_LEFT", "SWIPE_RIGHT", "HOLD_LOCK", "FOCUS_DETAIL"].includes(state);
  return {
    enabled: true,
    tracking: Boolean(center),
    tracking_mode: "frontend",
    state,
    gesture: action,
    gesture_action: action,
    action,
    cursor: center ? { x: center.x, y: center.y, z: center.z || 0, depth_level: "middle" } : EMPTY_CURSOR,
    hand: center ? {
      hand_detected: true,
      hand_confidence: confidence,
      landmarks_count: landmarksCount,
      hand_center: { x: Number(center.x.toFixed(3)), y: Number(center.y.toFixed(3)) },
    } : null,
    hand_active: Boolean(center),
    hand_ready: handReady,
    metrics,
    message,
    modelStatus: state === "HAND_MODEL_LOADING" ? "loading" : state === "HAND_MODEL_UNAVAILABLE" ? "unavailable" : "ready",
    gestureState: state,
    handDetected: Boolean(center),
    handConfidence: confidence,
    landmarksCount,
    handCenter: center ? { x: Number(center.x.toFixed(3)), y: Number(center.y.toFixed(3)) } : null,
    gestureFps: metrics.fps,
    lastError: error,
    snapshotStatus: snapshot,
    interaction: {
      hand_active: Boolean(center),
      hand_ready: handReady,
      hand_state: state,
      gesture_action: action,
      message,
      debug: {
        model: state === "HAND_MODEL_UNAVAILABLE" ? "unavailable" : state === "HAND_MODEL_LOADING" ? "loading" : "ready",
        hand_source: "frontend_hand_landmarker",
        gesture_frame_source: "gesture-frame",
        hand_model_loaded: state !== "HAND_MODEL_LOADING" && state !== "HAND_MODEL_UNAVAILABLE",
        hand_confidence: confidence,
        landmarks_count: landmarksCount,
        valid_hand: Boolean(center),
        snapshot,
        last_error: error,
        reject_reason: error || (center ? "none" : "no_landmarks"),
      },
    },
  };
}

export function createHandModelUnavailableStatus(reason = "hand_landmarker.task missing") {
  return createStatus({
    state: "HAND_MODEL_UNAVAILABLE",
    message: "手势模型未加载，键盘/鼠标可用",
    error: reason,
    snapshot: "idle",
  });
}

export class HandLandmarkerService {
  constructor({ onStatus } = {}) {
    this.onStatus = onStatus;
    this.handLandmarker = null;
    this.running = false;
    this.processing = false;
    this.canvas = document.createElement("canvas");
    this.canvas.width = 256;
    this.canvas.height = 192;
    this.context = this.canvas.getContext("2d", { willReadFrequently: false });
    this.consecutiveHands = 0;
    this.lostAt = 0;
    this.lastActionAt = 0;
    this.stableSince = 0;
    this.holdFired = false;
    this.focusFired = false;
    this.history = [];
    this.frameTimes = [];
    this.metrics = EMPTY_METRICS;
    this.lastEmitAt = 0;
    this.lastEmitSignature = "";
  }

  async start() {
    if (this.running) return;
    this.running = true;
    this.emit("HAND_MODEL_LOADING", "手势模型加载中");
    try {
      await assertModelExists();
      const vision = await FilesetResolver.forVisionTasks(HAND_WASM_PATH);
      this.handLandmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: HAND_MODEL_PATH,
          delegate: "CPU",
        },
        runningMode: "IMAGE",
        numHands: 1,
        minHandDetectionConfidence: 0.65,
        minHandPresenceConfidence: 0.65,
        minTrackingConfidence: 0.65,
      });
      this.emit("IDLE", "等待手势进入画面", null, 0, 0, null, "none", "gesture-frame");
      this.loop();
    } catch (error) {
      this.running = false;
      this.emit("HAND_MODEL_UNAVAILABLE", "手势模型未加载，键盘/鼠标可用", null, 0, 0, compactError(error), "none", "failed");
    }
  }

  stop() {
    this.running = false;
    this.handLandmarker?.close?.();
    this.handLandmarker = null;
  }

  async loop() {
    while (this.running) {
      const started = performance.now();
      await this.processFrame();
      const elapsed = performance.now() - started;
      await new Promise((resolve) => window.setTimeout(resolve, Math.max(40, HAND_FRAME_INTERVAL_MS - elapsed)));
    }
  }

  async processFrame() {
    if (this.processing || !this.handLandmarker) return;
    this.processing = true;
    const started = performance.now();
    try {
      const response = await fetch(`${API_BASE}/api/video/gesture-frame?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`gesture-frame ${response.status}`);
      const blob = await response.blob();
      const bitmap = await createImageBitmap(blob);
      this.canvas.width = bitmap.width || 256;
      this.canvas.height = bitmap.height || 192;
      this.context.drawImage(bitmap, 0, 0, this.canvas.width, this.canvas.height);
      bitmap.close?.();
      const result = this.handLandmarker.detect(this.canvas);
      this.handleResult(result, started);
    } catch (error) {
      this.emit("LOST", "gesture-frame 或手势检测失败", null, 0, 0, compactError(error), "none", "failed");
    } finally {
      this.processing = false;
    }
  }

  handleResult(result, started) {
    const landmarks = result.landmarks?.[0] || null;
    const confidence = handScore(result);
    const timestamp = performance.now();
    this.updateMetrics(timestamp, started);
    if (!landmarks?.length || landmarks.length < 21 || confidence < 0.65) {
      this.handleLost();
      return;
    }
    const center = averagePalm(landmarks);
    this.consecutiveHands += 1;
    this.lostAt = 0;
    this.history = [...this.history.filter((item) => timestamp - item.at <= 800), { at: timestamp, center }];
    const actionState = this.detectAction(timestamp, center);
    if (actionState) {
      this.emit(actionState.state, actionState.message, center, confidence, landmarks.length, null, actionState.action, "gesture-frame");
      return;
    }
    if (this.consecutiveHands < READY_STREAK) {
      this.emit("CANDIDATE", "检测到手部关键点，正在确认", center, confidence, landmarks.length, null, "none", "gesture-frame");
      return;
    }
    this.emit("HAND_READY", "手势已就绪，进入记忆浏览模式", center, confidence, landmarks.length, null, "none", "gesture-frame");
  }

  handleLost() {
    this.consecutiveHands = 0;
    this.history = [];
    this.stableSince = 0;
    this.holdFired = false;
    this.focusFired = false;
    const timestamp = performance.now();
    if (!this.lostAt) this.lostAt = timestamp;
    if (timestamp - this.lostAt > 1000) {
      this.emit("IDLE", "等待手势进入画面", null, 0, 0, null, "none", "gesture-frame");
      return;
    }
    this.emit("LOST", "手势短暂丢失，保持当前选择", null, 0, 0, null, "none", "gesture-frame");
  }

  detectAction(timestamp, center) {
    if (timestamp - this.lastActionAt < 800 || this.history.length < 2 || this.consecutiveHands < READY_STREAK) {
      return this.updateStable(timestamp);
    }
    const first = this.history[0].center;
    const deltaX = center.x - first.x;
    if (Math.abs(deltaX) >= SWIPE_THRESHOLD) {
      this.lastActionAt = timestamp;
      this.stableSince = 0;
      this.holdFired = false;
      this.focusFired = false;
      return deltaX < 0
        ? { state: "SWIPE_LEFT", action: "SWIPE_LEFT", message: "左挥切换上一条记忆" }
        : { state: "SWIPE_RIGHT", action: "SWIPE_RIGHT", message: "右挥切换下一条记忆" };
    }
    return this.updateStable(timestamp);
  }

  updateStable(timestamp) {
    const recent = this.history.filter((item) => timestamp - item.at <= 1000);
    if (recent.length < 4) return null;
    const xs = recent.map((item) => item.center.x);
    const ys = recent.map((item) => item.center.y);
    const stable = Math.max(...xs) - Math.min(...xs) < 0.055 && Math.max(...ys) - Math.min(...ys) < 0.055;
    if (!stable) {
      this.stableSince = 0;
      this.holdFired = false;
      this.focusFired = false;
      return null;
    }
    if (!this.stableSince) this.stableSince = recent[0].at;
    const stableMs = timestamp - this.stableSince;
    if (stableMs >= 1900 && !this.focusFired && timestamp - this.lastActionAt >= 1000) {
      this.focusFired = true;
      this.lastActionAt = timestamp;
      return { state: "FOCUS_DETAIL", action: "FOCUS_DETAIL", message: "展开当前记忆详情" };
    }
    if (stableMs >= 1000 && !this.holdFired && timestamp - this.lastActionAt >= 1000) {
      this.holdFired = true;
      this.lastActionAt = timestamp;
      return { state: "HOLD_LOCK", action: "HOLD_LOCK", message: "锁定当前视觉记忆" };
    }
    return null;
  }

  updateMetrics(timestamp, started) {
    this.frameTimes = [...this.frameTimes.filter((item) => timestamp - item <= 1000), timestamp];
    this.metrics = {
      fps: Number(this.frameTimes.length.toFixed(1)),
      latency_ms: Math.round(performance.now() - started),
      stable_frames: this.consecutiveHands,
      click_count: this.metrics.click_count || 0,
    };
  }

  emit(state, message, center = null, confidence = 0, landmarksCount = 0, error = null, action = "none", snapshot = "idle") {
    const now = performance.now();
    const important = action !== "none" || error || state === "HAND_MODEL_LOADING" || state === "HAND_MODEL_UNAVAILABLE";
    const signature = JSON.stringify({
      state,
      action,
      ready: ["HAND_READY", "SWIPE_LEFT", "SWIPE_RIGHT", "HOLD_LOCK", "FOCUS_DETAIL"].includes(state),
      landmarksCount,
      error,
      center: center ? [Math.round(center.x * 100), Math.round(center.y * 100)] : null,
    });
    if (!important && signature === this.lastEmitSignature) return;
    if (!important && now - this.lastEmitAt < HAND_STATUS_THROTTLE_MS) return;
    this.lastEmitAt = now;
    this.lastEmitSignature = signature;
    this.onStatus?.(createStatus({
      state,
      message,
      center,
      confidence,
      landmarksCount,
      metrics: this.metrics,
      error,
      action,
      snapshot,
    }));
  }
}
