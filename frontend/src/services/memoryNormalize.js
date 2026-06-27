const UNKNOWN_LABEL = "未知物体";

export function normalizeMemoryStatus(raw = {}) {
  const memories = (raw.memories || raw.objects || []).map(normalizeMemoryItem);
  const latest = raw.latest_memory ? normalizeMemoryItem(raw.latest_memory) : memories[0] || null;
  return {
    ...raw,
    camera_status: raw.camera_status || raw.camera || "offline",
    memory_count: raw.memory_count ?? memories.length,
    object_count: raw.object_count ?? memories.length,
    latest_memory: latest,
    latest_event: raw.latest_event || (latest ? `正在观察：${latest.label_zh}` : "视觉记忆等待新的画面变化"),
    interaction: raw.interaction || {},
    memories,
    objects: memories,
  };
}

export function normalizeMemoryItem(item = {}) {
  const labelZh = item.label_zh || item.label_cn || (item.label === "unknown" ? UNKNOWN_LABEL : item.label) || UNKNOWN_LABEL;
  const position = item.position || item.position_hint || "画面中央";
  return {
    ...item,
    id: item.id || item.object_id || `${item.label || "unknown"}_${position}`,
    object_id: item.object_id || item.id,
    label: item.label || "unknown",
    label_zh: labelZh === "visual_target" || labelZh === "视觉目标" ? UNKNOWN_LABEL : labelZh,
    label_cn: labelZh,
    position,
    position_hint: position,
    center: item.center || null,
    relative_position: item.relative_position || zoneFromPosition(position),
    size_level: item.size_level || "medium",
    distance_hint: item.distance_hint || "middle",
    confidence: Number(item.confidence || 0),
    seen_count: item.seen_count || 1,
    source: item.source || "unknown",
  };
}

function zoneFromPosition(position) {
  const map = {
    "画面左上": { x: 0.17, y: 0.17, zone: "left_upper" },
    "画面上方": { x: 0.5, y: 0.17, zone: "center_upper" },
    "画面右上": { x: 0.83, y: 0.17, zone: "right_upper" },
    "画面左侧": { x: 0.17, y: 0.5, zone: "left_middle" },
    "画面中央": { x: 0.5, y: 0.5, zone: "center_middle" },
    "画面右侧": { x: 0.83, y: 0.5, zone: "right_middle" },
    "画面左下": { x: 0.17, y: 0.83, zone: "left_lower" },
    "画面下方": { x: 0.5, y: 0.83, zone: "center_lower" },
    "画面右下": { x: 0.83, y: 0.83, zone: "right_lower" },
  };
  return map[position] || map["画面中央"];
}

export function memoryStatusSignature(status = {}) {
  const memories = status.memories || status.objects || [];
  return JSON.stringify({
    version: status.version,
    camera_status: status.camera_status || status.camera,
    memory_count: status.memory_count,
    latest_id: status.latest_memory?.id,
    interaction: status.interaction,
    memories: memories.map((item) => [item.id, item.label_zh || item.label_cn, item.position || item.position_hint, item.seen_count, item.last_seen, item.confidence]),
  });
}

export function sourceLabel(source) {
  if (source === "onnx" || source === "model") return "边缘视觉模型";
  if (source === "rule") return "轻量规则识别";
  return "来源待确认";
}

export function formatConfidence(confidence) {
  if (!confidence) return "置信度待确认";
  return `置信度 ${Math.round(confidence * 100)}%`;
}
