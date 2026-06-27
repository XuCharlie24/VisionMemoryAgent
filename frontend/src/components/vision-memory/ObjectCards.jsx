import { formatConfidence, sourceLabel } from "../../services/memoryNormalize.js";

function zoneIndex(zone) {
  const map = {
    left_upper: 0, center_upper: 1, right_upper: 2,
    left_middle: 3, center_middle: 4, right_middle: 5,
    left_lower: 6, center_lower: 7, right_lower: 8,
  };
  return map[zone] ?? 4;
}

export default function ObjectCards({ objects, selectedId, lockedId, latestId, detailId, onSelect }) {
  if (!objects.length) {
    return <div className="empty-state">等待目标进入画面</div>;
  }
  return (
    <div className="object-list">
      {objects.slice(0, 10).map((object) => (
        <article
          className={`object-card ${selectedId === object.id ? "selected" : ""} ${lockedId === object.id ? "locked" : ""}`}
          key={object.id}
          role="button"
          tabIndex={0}
          onClick={() => onSelect?.(object.id)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") onSelect?.(object.id);
          }}
        >
          <div>
            <strong>{object.label_zh || "未知物体"}</strong>
            <span>{object.position}</span>
          </div>
          <div className="memory-card-body">
            <div className="mini-map">
              {Array.from({ length: 9 }).map((_, index) => (
                <i key={index} className={index === zoneIndex(object.relative_position?.zone) ? "active" : ""} />
              ))}
            </div>
            <div className="confidence-meter">
              <span style={{ width: `${Math.round((object.confidence || 0) * 100)}%` }} />
            </div>
          </div>
          <p className="memory-badges">
            {selectedId === object.id && <span>当前选中</span>}
            {lockedId === object.id && <span>已锁定</span>}
            {latestId === object.id && <span>最新记忆</span>}
            {detailId === object.id && <span>详情展开</span>}
          </p>
          <footer>
            <span>已观察 {object.seen_count} 次 · {formatConfidence(object.confidence)}</span>
            <span>来源：{sourceLabel(object.source)}</span>
          </footer>
        </article>
      ))}
    </div>
  );
}
