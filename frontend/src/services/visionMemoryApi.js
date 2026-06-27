import { get, post } from "./rdkApi";

export function getVisionMemoryStatus() {
  return get("/api/memory/status");
}

export function resetVisionMemory() {
  return post("/api/memory/reset");
}
