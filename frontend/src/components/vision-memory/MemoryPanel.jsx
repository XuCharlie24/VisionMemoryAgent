import ObjectCards from "./ObjectCards.jsx";

const FILTERS = [
  ["all", "全部"],
  ["locked", "已锁定"],
  ["confident", "高置信"],
  ["recent", "最近出现"],
  ["unknown", "未知"],
];

const SORTS = [
  ["recent", "最近"],
  ["seen", "观察次数"],
  ["confidence", "置信度"],
];

export default function MemoryPanel({ memory, selectedId, lockedId, detailId, filter, sort, onFilter, onSort, onSelect }) {
  const latest = memory.latest_memory;
  const memories = memory.memories || [];
  const visible = memories
    .filter((item) => {
      if (filter === "locked") return item.id === lockedId;
      if (filter === "confident") return item.confidence >= 0.75;
      if (filter === "recent") return item.id === latest?.id || item.seen_count > 1;
      if (filter === "unknown") return item.label === "unknown";
      return true;
    })
    .slice()
    .sort((left, right) => {
      if (sort === "seen") return (right.seen_count || 0) - (left.seen_count || 0);
      if (sort === "confidence") return (right.confidence || 0) - (left.confidence || 0);
      return String(right.last_seen || "").localeCompare(String(left.last_seen || ""));
    });
  return (
    <section className="panel memory-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Visual Memory Archive</p>
          <h2>视觉记忆档案</h2>
        </div>
        <strong className="large-count">{memory.memory_count}</strong>
      </div>
      <div className="archive-stats">
        <div><strong>{memory.memory_count}</strong><span>总记忆</span></div>
        <div><strong>{memory.object_count || 0}</strong><span>观察中</span></div>
        <div><strong>{lockedId ? 1 : 0}</strong><span>已锁定</span></div>
        <div><strong>{memories.length}</strong><span>本次新增</span></div>
      </div>
      <div className="event-box">
        <span>最新记忆</span>
        <p>{latest ? `${latest.label_zh} · ${latest.position} · ${Math.round(latest.confidence * 100)}% · 已观察 ${latest.seen_count} 次` : memory.latest_event}</p>
      </div>
      <div className="archive-controls">
        <div>{FILTERS.map(([key, label]) => <button key={key} className={filter === key ? "selected" : ""} onClick={() => onFilter?.(key)}>{label}</button>)}</div>
        <select value={sort} onChange={(event) => onSort?.(event.target.value)}>
          {SORTS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </div>
      <ObjectCards objects={visible} selectedId={selectedId} lockedId={lockedId} latestId={latest?.id} detailId={detailId} onSelect={onSelect} />
    </section>
  );
}
