import { get, post } from "./rdkApi";

export function getVisionTouchStatus() {
  return get("/api/vision-touch/status");
}

export function getVisionTouchConfig() {
  return get("/api/vision-touch/config");
}

export function updateVisionTouchConfig(update) {
  return post("/api/vision-touch/config", update);
}
