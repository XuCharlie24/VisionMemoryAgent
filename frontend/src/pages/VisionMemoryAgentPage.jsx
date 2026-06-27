import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Cpu, Database, RadioTower, ScanLine } from "lucide-react";
import CameraPanel from "../components/camera/CameraPanel.jsx";
import MemoryPanel from "../components/vision-memory/MemoryPanel.jsx";
import MemoryTimeline from "../components/vision-memory/MemoryTimeline.jsx";
import GestureStatusPanel from "../components/vision-touch/GestureStatusPanel.jsx";
import AirCursor from "../components/vision-touch/AirCursor.jsx";
import HologramStage from "../components/hologram/HologramStage.jsx";
import { API_BASE, getCurrentStatus } from "../services/rdkApi";
import { createHandModelUnavailableStatus, HandLandmarkerService } from "../services/HandLandmarkerService.js";
import { memoryStatusSignature, normalizeMemoryStatus } from "../services/memoryNormalize.js";
import { getVisionMemoryStatus, resetVisionMemory } from "../services/visionMemoryApi";

const fallbackMemory = {
  enabled: true,
  camera: "offline",
  object_count: 0,
  memory_count: 0,
  memories: [],
  objects: [],
  latest_memory: null,
  latest_event: "视觉记忆等待新的画面变化",
  message: "视觉记忆运行中",
};

const fallbackTouch = {
  enabled: true,
  tracking: false,
  tracking_mode: "hand",
  state: "HAND_MODEL_UNAVAILABLE",
  gesture: "none",
  action: "none",
  cursor: { x: 0.5, y: 0.5, z: 0, depth_level: "far" },
  hand: null,
  metrics: { fps: 0, latency_ms: 0, stable_frames: 0, click_count: 0 },
  message: "手势模型未加载，当前使用键盘/鼠标交互",
};

function createEvent(type, title, detail, memoryId = null, level = "normal") {
  return {
    id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
    at: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
    type,
    title,
    detail,
    memory_id: memoryId,
    level,
  };
}

export default function VisionMemoryAgentPage() {
  const [status, setStatus] = useState({ camera: "offline", vision_memory: fallbackMemory, vision_touch: fallbackTouch });
  const [memory, setMemory] = useState(fallbackMemory);
  const [touch, setTouch] = useState(() => createHandModelUnavailableStatus("initializing"));
  const [apiOnline, setApiOnline] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [lockedId, setLockedId] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [archiveFilter, setArchiveFilter] = useState("all");
  const [archiveSort, setArchiveSort] = useState("recent");
  const [interactionState, setInteractionState] = useState("观察中");
  const [stageAction, setStageAction] = useState(null);
  const [events, setEvents] = useState(() => [createEvent("system", "视觉模型已加载", "目标检测由 RDK X3 后台异步执行", null, "important")]);
  const [toast, setToast] = useState(null);
  const pollSignaturesRef = useRef({});
  const consumedGestureRef = useRef({ state: "", at: 0 });
  const previousMemoriesRef = useRef(new Map());
  const eventThrottleRef = useRef({});
  const touchSignatureRef = useRef("");
  const handModelReadyRef = useRef(false);

  useEffect(() => {
    const poll = (key, fn, onData, delay, signature = JSON.stringify) => {
      let mounted = true;
      const run = async () => {
        try {
          const data = await fn();
          if (mounted) {
            const nextSignature = signature(data);
            if (pollSignaturesRef.current[key] !== nextSignature) {
              pollSignaturesRef.current[key] = nextSignature;
              onData(data);
            }
            setApiOnline(true);
          }
        } catch {
          if (mounted) setApiOnline(false);
        }
      };
      run();
      const timer = window.setInterval(run, delay);
      return () => {
        mounted = false;
        window.clearInterval(timer);
      };
    };
    const cleanups = [
      poll("status", getCurrentStatus, setStatus, 1500, (data) => JSON.stringify({
        camera: data.camera,
        version: data.vision_memory?.version,
        stream_fps: data.vision_memory?.performance?.stream_fps,
        gesture_fps: data.vision_memory?.performance?.gesture_frame_requests_per_sec,
        detector_ms: data.vision_memory?.performance?.detector_latency_ms,
        touch: data.vision_touch?.interaction || data.vision_touch || {},
      })),
      poll("memory", getVisionMemoryStatus, setMemory, 1000, (data) => `${data.version ?? "v0"}-${memoryStatusSignature(data)}`),
    ];
    return () => cleanups.forEach((cleanup) => cleanup());
  }, []);

  const mergedStatusMemory = useMemo(() => normalizeMemoryStatus({ ...fallbackMemory, ...status.vision_memory }), [status]);
  const normalizedMemory = useMemo(() => normalizeMemoryStatus({ ...fallbackMemory, ...memory }), [memory]);
  const mergedMemoryInteraction = useMemo(() => ({
    ...(mergedStatusMemory.interaction || {}),
    ...(normalizedMemory.interaction || {}),
  }), [mergedStatusMemory.interaction, normalizedMemory.interaction]);
  const mergedMemory = useMemo(() => ({
    ...normalizedMemory,
    camera_status: normalizedMemory.camera_status || mergedStatusMemory.camera_status,
    interaction: mergedMemoryInteraction,
    performance: {
      ...(normalizedMemory.performance || {}),
      ...(mergedStatusMemory.performance || {}),
    },
  }), [mergedMemoryInteraction, mergedStatusMemory.camera_status, mergedStatusMemory.performance, normalizedMemory]);
  const cameraState = status.camera || mergedMemory.camera_status || "offline";
  const mergedTouch = useMemo(() => ({ ...fallbackTouch, ...touch }), [touch]);
  const rawInteraction = useMemo(() => ({
    ...(mergedMemory.interaction || {}),
    ...(mergedTouch.interaction || {}),
  }), [mergedMemory.interaction, mergedTouch.interaction]);
  const memories = mergedMemory.memories || [];
  const selectedMemory = memories.find((item) => item.id === selectedId) || memories[0] || null;
  const lockedMemory = memories.find((item) => item.id === lockedId) || null;
  const interaction = useMemo(() => ({
    ...rawInteraction,
    selected_memory_id: selectedMemory?.id || null,
    locked_memory_id: lockedMemory?.id || null,
    detail_memory_id: detailId || null,
    selected_label_zh: selectedMemory?.label_zh || null,
    locked_label_zh: lockedMemory?.label_zh || null,
  }), [detailId, lockedMemory, rawInteraction, selectedMemory]);

  const showToast = useCallback((message, type = "ok") => {
    setToast({ message, type });
    window.setTimeout(() => setToast(null), 2200);
  }, []);

  const pushEvent = useCallback((type, title, detail, memoryId = null, level = "normal") => {
    setEvents((items) => [createEvent(type, title, detail, memoryId, level), ...items].slice(0, 20));
  }, []);

  const selectByOffset = useCallback((offset, source = "keyboard") => {
    if (!memories.length) {
      if (source === "gesture") pushEvent("gesture_action", "暂无可操作记忆", "手势已识别，但当前没有视觉记忆节点", null, "muted");
      return;
    }
    const currentIndex = Math.max(0, memories.findIndex((item) => item.id === (selectedMemory?.id || selectedId)));
    const nextIndex = (currentIndex + offset + memories.length) % memories.length;
    setSelectedId(memories[nextIndex].id);
    setInteractionState(offset < 0 ? `切换到上一条记忆：${memories[nextIndex].label_zh}` : `切换到下一条记忆：${memories[nextIndex].label_zh}`);
    pushEvent(
      source === "gesture" ? "gesture_action" : "system",
      offset < 0 ? `切换到上一条记忆：${memories[nextIndex].label_zh}` : `切换到下一条记忆：${memories[nextIndex].label_zh}`,
      source === "gesture" ? (offset < 0 ? "左挥触发上一条记忆" : "右挥触发下一条记忆") : "键盘快捷键切换记忆",
      memories[nextIndex].id,
      source === "gesture" ? "important" : "normal",
    );
    setStageAction(offset < 0 ? "previous" : "next");
    window.setTimeout(() => setStageAction(null), 900);
  }, [memories, pushEvent, selectedId, selectedMemory]);

  const lockSelected = useCallback((source = "keyboard") => {
    const target = selectedMemory || memories[0];
    if (!target) return;
    setSelectedId(target.id);
    setLockedId(target.id);
    setInteractionState(`已锁定记忆：${target.label_zh}`);
    pushEvent("memory_locked", `锁定视觉记忆：${target.label_zh}`, source === "gesture" ? "停留手势触发锁定" : "键盘确认锁定", target.id, "important");
  }, [memories, pushEvent, selectedMemory]);

  const focusSelected = useCallback((source = "keyboard") => {
    const target = selectedMemory || memories[0];
    if (!target) return;
    setSelectedId(target.id);
    setDetailId(target.id);
    setInteractionState(`展开记忆详情：${target.label_zh}`);
    pushEvent("memory_focused", `展开记忆详情：${target.label_zh}`, source === "gesture" ? "长停留手势触发展开详情" : "快捷键展开详情", target.id, "important");
  }, [memories, pushEvent, selectedMemory]);

  const exitDetail = useCallback(() => {
    setDetailId(null);
    setInteractionState(selectedMemory ? `当前选中：${selectedMemory.label_zh}` : "观察中");
  }, [selectedMemory]);

  const selectMemory = useCallback((id) => {
    const target = memories.find((item) => item.id === id);
    if (!target) return;
    setSelectedId(id);
    setInteractionState(`当前选中：${target.label_zh}`);
  }, [memories]);

  const handleResetMemory = useCallback(async () => {
    try {
      await resetVisionMemory();
      setMemory(fallbackMemory);
      setSelectedId(null);
      setLockedId(null);
      setDetailId(null);
      setArchiveFilter("all");
      setArchiveSort("recent");
      setInteractionState("观察中");
      previousMemoriesRef.current = new Map();
      setEvents([createEvent("system", "记忆库已清空", "视觉记忆节点和事件时间线已重置", null, "important")]);
      showToast("记忆库已重置", "ok");
    } catch {
      showToast("记忆重置失败，请检查板端 API", "warn");
    }
  }, [showToast]);

  useEffect(() => {
    const service = new HandLandmarkerService({
      onStatus: (nextStatus) => {
        const signature = JSON.stringify({
          state: nextStatus.state,
          action: nextStatus.gesture_action,
          ready: nextStatus.hand_ready,
          center: nextStatus.hand?.hand_center,
          fps: nextStatus.metrics?.fps,
          error: nextStatus.interaction?.debug?.reject_reason,
        });
        if (touchSignatureRef.current === signature) return;
        touchSignatureRef.current = signature;
        setTouch(nextStatus);
        if (nextStatus.state === "HAND_READY") {
          const now = Date.now();
          if (!eventThrottleRef.current.gesture_ready || now - eventThrottleRef.current.gesture_ready > 6000) {
            eventThrottleRef.current.gesture_ready = now;
            pushEvent("gesture_ready", "检测到手势", "进入记忆浏览模式", null, "important");
          }
        }
        if (nextStatus.state === "HAND_MODEL_UNAVAILABLE") {
          pushEvent("system", "手势模型加载失败", nextStatus.message, null, "important");
        }
        if (nextStatus.state === "IDLE" && !handModelReadyRef.current) {
          handModelReadyRef.current = true;
          pushEvent("system", "手势模型已加载", "MediaPipe Hands 已从本地资源启动", null, "important");
        }
      },
    });
    service.start();
    return () => service.stop();
  }, [pushEvent]);

  useEffect(() => {
    const previous = previousMemoriesRef.current;
    const nextMap = new Map();
    const now = Date.now();
    memories.forEach((item) => {
      nextMap.set(item.id, item);
      const old = previous.get(item.id);
      const confidence = Math.round((item.confidence || 0) * 100);
      if (!old) {
        pushEvent("object_seen", `识别到${item.label_zh}`, `${item.position} · 置信度 ${confidence}%`, item.id, item.label === "person" ? "muted" : "important");
        return;
      }
      if ((old.position || old.position_hint) !== (item.position || item.position_hint)) {
        pushEvent("object_moved", `${item.label_zh}位置变化`, `${old.position || old.position_hint} → ${item.position || item.position_hint}`, item.id, item.label === "person" ? "muted" : "important");
        return;
      }
      if ((item.seen_count || 0) > (old.seen_count || 0)) {
        const key = `updated_${item.id}`;
        const minGap = item.label === "person" ? 9000 : 3000;
        if (!eventThrottleRef.current[key] || now - eventThrottleRef.current[key] > minGap) {
          eventThrottleRef.current[key] = now;
          pushEvent("object_updated", `${item.label_zh}持续出现`, `已观察 ${item.seen_count} 次`, item.id, "normal");
        }
      }
    });
    previousMemoriesRef.current = nextMap;
  }, [memories, pushEvent]);

  useEffect(() => {
    if (!memories.length) {
      setSelectedId(null);
      setLockedId(null);
      setDetailId(null);
      return;
    }
    if (!selectedId || !memories.some((item) => item.id === selectedId)) {
      setSelectedId(memories[0].id);
    }
  }, [memories, selectedId]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "ArrowLeft") selectByOffset(-1);
      if (event.key === "ArrowRight") selectByOffset(1);
      if (event.key === "Enter") lockSelected();
      if (event.key === " ") {
        event.preventDefault();
        focusSelected();
      }
      if (event.key === "Escape") exitDetail();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [exitDetail, focusSelected, lockSelected, selectByOffset]);

  useEffect(() => {
    const handState = interaction.hand_state || mergedTouch.state;
    const gestureAction = interaction.gesture_action || mergedTouch.gesture_action;
    const now = Date.now();
    const actionKey = `${handState}-${gestureAction}-${Math.floor(now / 500)}`;
    if (gestureAction && consumedGestureRef.current.state !== actionKey) {
      consumedGestureRef.current = { state: actionKey, at: now };
      if (gestureAction === "previous" || gestureAction === "SWIPE_LEFT" || handState === "SWIPE_LEFT") {
        selectByOffset(-1, "gesture");
        return;
      }
      if (gestureAction === "next" || gestureAction === "SWIPE_RIGHT" || handState === "SWIPE_RIGHT") {
        selectByOffset(1, "gesture");
        return;
      }
      if (gestureAction === "lock" || gestureAction === "HOLD_LOCK" || handState === "HOLD_LOCK") {
        lockSelected("gesture");
        return;
      }
      if (gestureAction === "FOCUS_DETAIL" || handState === "FOCUS_DETAIL") {
        focusSelected("gesture");
        return;
      }
    }
    if (handState === "HAND_MODEL_UNAVAILABLE" && interactionState !== "手势模型未加载，当前使用键盘/鼠标交互") {
      setInteractionState("手势模型未加载，当前使用键盘/鼠标交互");
      return;
    }
    if (handState === "FRONTEND_CONTROLLED" && interactionState !== "手势由前端处理") {
      setInteractionState("手势由前端处理");
      return;
    }
    if (handState === "HAND_READY" && !interactionState.startsWith("已锁定记忆")) {
      setInteractionState("手势已就绪");
      return;
    }
    if (handState === "CANDIDATE" && !interactionState.startsWith("已锁定记忆")) {
      setInteractionState("检测到疑似手");
      return;
    }
    if (handState === "LOST" && !interactionState.startsWith("已锁定记忆")) {
      setInteractionState("手势短暂丢失，保持就绪");
      return;
    }
    if (!mergedTouch.tracking && !interactionState.startsWith("已锁定记忆")) setInteractionState("观察中");
  }, [focusSelected, interaction, interactionState, lockSelected, mergedTouch, selectByOffset]);

  return (
    <main className="vma-shell">
      <AirCursor touch={mergedTouch} />
      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
      <header className="vma-header">
        <div>
          <p className="eyebrow">RDK X3 Edge Vision</p>
          <h1>Vision Memory Agent</h1>
          <p className="subtitle">基于 RDK X3 的视觉记忆与无接触空间交互智能体</p>
        </div>
        <div className="status-strip">
          <span><Cpu size={15} /> RDK X3</span>
          <span><ScanLine size={15} /> USB Camera</span>
          <span><Database size={15} /> Edge AI</span>
          <span className={cameraState === "online" ? "ok" : "warn"}>{cameraState === "online" ? "Camera Online" : "Camera Offline"}</span>
          <span><RadioTower size={15} /> {API_BASE}</span>
        </div>
      </header>

      <section className="dashboard-grid">
        <CameraPanel cameraState={cameraState} memory={mergedMemory} touch={mergedTouch} />
        <HologramStage memory={mergedMemory} touch={mergedTouch} apiOnline={apiOnline} selectedId={selectedMemory?.id} lockedId={lockedId} detailId={detailId} stageAction={stageAction} interaction={interaction} />
        <MemoryPanel memory={mergedMemory} selectedId={selectedMemory?.id} lockedId={lockedId} detailId={detailId} filter={archiveFilter} sort={archiveSort} onFilter={setArchiveFilter} onSort={setArchiveSort} onSelect={selectMemory} />
      </section>

      <section className="bottom-grid">
        <GestureStatusPanel touch={mergedTouch} interaction={interaction} interactionState={interactionState} selectedMemory={selectedMemory} lockedMemory={lockedMemory} onResetMemory={handleResetMemory} />
        <section className="panel event-timeline-panel">
          <MemoryTimeline events={events} onSelect={selectMemory} />
        </section>
      </section>
    </main>
  );
}
