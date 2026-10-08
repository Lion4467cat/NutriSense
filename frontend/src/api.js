const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8731";

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return res.json();
}

export function getMenu() {
  return get("/menu");
}

export function getHealth() {
  return get("/health");
}

export async function analyze({ file, day, band, serving_style }) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("day", day);
  fd.append("band", band);
  if (serving_style) fd.append("serving_style", serving_style);
  const res = await fetch(`${API_BASE}/analyze`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(`API ${res.status} on /analyze`);
  return res.json();
}
