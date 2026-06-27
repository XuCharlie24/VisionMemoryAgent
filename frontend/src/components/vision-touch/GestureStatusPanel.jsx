import { RotateCcw } from "lucide-react";

export default function GestureStatusPanel({ touch, interaction, interactionState, selectedMemory, lockedMemory, onResetMemory }) {
  const metrics = touch.metrics || {};
  const handReady = interaction?.hand_ready || touch.hand_ready;
  const state = interaction?.hand_state || touch.state || "IDLE";
  const debug = interaction?.debug || {};
  const recentAction = interaction?.message || touch.message || "等待手势进入识别区域";
  const lastError = touch.lastError || debug.last_error || debug.reject_reason;
  const title = {
    FRONTEND_CONTROLLED: "前端手势接管",
    HAND_MODEL_LOADING: "手势模型加载中",
    HAND_MODEL_UNAVAILABLE: "手势模型未加载",
    IDLE: "等待手势",
    DISABLED: "手势模型未启用",
    CANDIDATE: "检测到疑似手",
    HAND_READY: "手势已就绪",
    SWIPE_LEFT: "已切换上一条记忆",
    SWIPE_RIGHT: "已切换下一条记忆",
    HOLD_LOCK: "已锁定记忆",
    FOCUS_DETAIL: "已展开记忆详情",
    LOST: "手势短暂丢失",
  }[state] || interactionState;
  const actionText = {
    FRONTEND_CONTROLLED: "使用前端交互",
    HAND_MODEL_LOADING: "正在准备本地模型",
    HAND_MODEL_UNAVAILABLE: "使用键盘/鼠标交互",
    IDLE: "等待挥手",
    DISABLED: "使用键盘/鼠标交互",
    CANDIDATE: "请保持手掌在画面侧边",
    HAND_READY: "左右挥手切换记忆",
    SWIPE_LEFT: "左挥切换上一条",
    SWIPE_RIGHT: "右挥切换下一条",
    HOLD_LOCK: "停留锁定",
    FOCUS_DETAIL: "长停留展开详情",
    LOST: "保持当前选择",
  }[state] || "等待挥手";
  return (
    <section className="panel gesture-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Gesture Interaction</p>
          <h2>手势交互 · {title}</h2>
        </div>
        <button className="icon-button compact" onClick={onResetMemory} title="Reset memory">
          <RotateCcw size={15} />
          <span>Reset</span>
        </button>
      </div>
      {lockedMemory && <div className="lock-banner">已锁定记忆：{lockedMemory.label_zh}</div>}
      <div className={`ready-banner ${handReady ? "active" : ""}`}>
        <strong>当前选中：{selectedMemory?.label_zh || "暂无记忆"}</strong>
        <span>{recentAction}</span>
      </div>
      <div className="gesture-help">
        <span>当前操作：{actionText}</span>
        <strong>左右挥手切换 · 停留锁定 · Space 展开详情 · 键鼠备用</strong>
      </div>
      <div className="gesture-chip-row">
        <span className={`state-chip ${state.toLowerCase()}`}>{state}</span>
        <span>model: {debug.model || (debug.hand_model_loaded ? "ready" : "unavailable")}</span>
        <span>fps: {metrics.fps || 0}</span>
        <span>landmarks: {touch.landmarksCount || debug.landmarks_count || 0}</span>
        <span>conf: {Number(debug.hand_confidence || touch.handConfidence || 0).toFixed(2)}</span>
        <span>snapshot: {touch.snapshotStatus || debug.snapshot || "idle"}</span>
      </div>
      {lastError && lastError !== "none" && (
        <p className="gesture-error" title={lastError}>
          {lastError}
        </p>
      )}
      <div className="gesture-compact-meta">
        <span>{interactionState}</span>
        <span>{handReady ? "HAND_READY" : "键盘/鼠标可用"}</span>
      </div>
    </section>
  );
}
