import { API_BASE } from "../../services/rdkApi";

export default function CameraPanel({ cameraState, memory, touch }) {
  const perf = memory.performance || {};
  const handSource = touch.interaction?.debug?.gesture_frame_source || touch.interaction?.debug?.hand_source || "idle";
  return (
    <section className="panel camera-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Camera Feed</p>
          <h2>USB Vision Stream</h2>
        </div>
        <span className={cameraState === "online" ? "live-pill" : "live-pill offline"}>{cameraState === "online" ? "LIVE" : "OFFLINE"}</span>
      </div>
      <div className="video-frame">
        <img src={`${API_BASE}/api/video/stream`} alt="RDK X3 USB camera stream" />
      </div>
      <div className="metric-row">
        <div><strong>{memory.memory_count}</strong><span>已记住</span></div>
        <div><strong>{memory.object_count}</strong><span>观察中</span></div>
        <div><strong>{touch.metrics?.click_count || 0}</strong><span>点击</span></div>
      </div>
      <div className="perf-strip">
        <span>mode {perf.demo_smooth_mode || perf.smooth_mode ? "smooth" : "normal"}</span>
        <span>stream {perf.stream_fps || 0} fps</span>
        <span>gesture {perf.gesture_frame_fps || perf.gesture_frame_requests_per_sec || 0}/s</span>
        <span>detector {perf.detector_latency_ms || 0} ms</span>
        <span>interval {perf.detector_interval_ms || 0} ms</span>
        <span>hand {handSource}</span>
      </div>
    </section>
  );
}
