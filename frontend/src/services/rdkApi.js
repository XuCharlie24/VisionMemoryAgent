export const API_BASE = (import.meta.env.VITE_RDK_API_BASE || "http://172.20.10.2:8000").replace(/。$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function get(path) {
  return request(path);
}

export function post(path, body = {}) {
  return request(path, { method: "POST", body: JSON.stringify(body) });
}

export function getCurrentStatus() {
  return get("/api/status/current");
}
