// Central server URL. Build-time override via VITE_SERVER_URL; runtime override
// via the `server` field in localStorage (UI lets you switch it).
const fromEnv = import.meta.env.VITE_SERVER_URL;
const fromLs = typeof localStorage !== "undefined" ? localStorage.getItem("fl.server") : null;

export const DEFAULT_SERVER = fromLs || fromEnv || "http://localhost:8000";

export function saveServer(url) {
  localStorage.setItem("fl.server", url);
}
