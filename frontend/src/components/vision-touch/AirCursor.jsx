import { useEffect, useRef } from "react";

export default function AirCursor({ touch }) {
  const cursorRef = useRef(null);

  useEffect(() => {
    if (!cursorRef.current || !touch?.tracking) return;
    cursorRef.current.style.setProperty("--cursor-x", `${(touch.cursor?.x || 0.5) * 100}%`);
    cursorRef.current.style.setProperty("--cursor-y", `${(touch.cursor?.y || 0.5) * 100}%`);
  }, [touch]);

  if (!touch?.tracking) return null;
  const isClick = touch.state === "CLICK";
  return (
    <div
      ref={cursorRef}
      className={`air-cursor ${touch.cursor?.depth_level || "far"} ${isClick ? "clicking" : ""}`}
    />
  );
}
