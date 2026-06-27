import { Eye, Focus, Hand, Lock, MoveRight, RotateCcw, Sparkles } from "lucide-react";

const ICONS = {
  object_seen: Eye,
  object_updated: RotateCcw,
  object_moved: MoveRight,
  memory_locked: Lock,
  memory_focused: Focus,
  gesture_ready: Hand,
  gesture_action: Hand,
  system: Sparkles,
};

export default function MemoryTimeline({ events = [], onSelect }) {
  return (
    <div className="visual-event-timeline">
      <div className="timeline-heading">
        <div>
          <p className="eyebrow">Visual Event Timeline</p>
          <h3>视觉事件时间线</h3>
        </div>
        <span>{events.length} events</span>
      </div>
      <div className="timeline-list">
        {events.slice(0, 8).map((event) => {
          const Icon = ICONS[event.type] || Sparkles;
          const clickable = Boolean(event.memory_id && onSelect);
          return (
            <button
              type="button"
              key={event.id}
              className={`timeline-event ${event.level || "normal"} ${clickable ? "clickable" : ""}`}
              onClick={() => clickable && onSelect(event.memory_id)}
              disabled={!clickable}
            >
              <span className="event-icon"><Icon size={15} /></span>
              <span className="event-copy">
                <strong>{event.title}</strong>
                <small>{event.detail}</small>
              </span>
              <time>{event.at}</time>
            </button>
          );
        })}
      </div>
    </div>
  );
}
