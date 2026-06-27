import { RotateCcw, SlidersHorizontal } from "lucide-react";
import { updateVisionTouchConfig } from "../../services/visionTouchApi";

export default function TouchControlPanel({ config, setConfig, onResetMemory }) {
  const current = config || {
    tracking_mode: "hand",
    smoothing_alpha: 0.35,
    click_cooldown_ms: 800,
    active_area_min: 8000,
    active_area_max: 45000,
    press_hold_ms: 300,
  };

  const update = async (patch) => {
    try {
      const next = await updateVisionTouchConfig(patch);
      setConfig(next);
    } catch {
      setConfig({ ...current, ...patch });
    }
  };

  return (
    <section className="panel control-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Control Surface</p>
          <h2>交互参数</h2>
        </div>
        <SlidersHorizontal size={20} />
      </div>
      <div className="segmented">
        <button className={current.tracking_mode === "hand" ? "selected" : ""} onClick={() => update({ tracking_mode: "hand" })}>Hand</button>
      </div>
      <label className="range-field">
        <span>smoothing_alpha</span>
        <input type="range" min="0.05" max="0.95" step="0.05" value={current.smoothing_alpha} onChange={(event) => update({ smoothing_alpha: Number(event.target.value) })} />
        <strong>{Number(current.smoothing_alpha).toFixed(2)}</strong>
      </label>
      <div className="control-actions">
        <button className="icon-button" onClick={onResetMemory} title="Reset memory">
          <RotateCcw size={18} />
          <span>Reset Memory</span>
        </button>
      </div>
    </section>
  );
}
