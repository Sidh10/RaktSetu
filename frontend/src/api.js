// Thin fetch wrapper. The demo identity travels in X-Demo-User (ADR-004: NOT real authentication).
let currentUser = "";

export function setUser(id) {
  currentUser = id || "";
}

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(method, path, body, params) {
  const url = new URL(path, window.location.origin);
  Object.entries(params || {}).forEach(([k, v]) => v !== undefined && v !== null && url.searchParams.set(k, v));
  const headers = { "Content-Type": "application/json" };
  if (currentUser) headers["X-Demo-User"] = currentUser;
  const r = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    const e = (data && data.error) || {};
    throw new ApiError(r.status, e.code || "http_error", e.message || r.statusText);
  }
  return data;
}

export const get = (path, params) => request("GET", path, undefined, params);
export const post = (path, body = {}) => request("POST", path, body);
export const patch = (path, body = {}) => request("PATCH", path, body);

// Browser storage is a convenience only (remembered role); it may be unavailable.
export function loadPref(key, fallback) {
  try {
    const v = window.localStorage.getItem(key);
    return v === null ? fallback : v;
  } catch {
    return fallback;
  }
}

export function savePref(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

export function istTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" });
}

export function istDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export const GROUPS = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"];
