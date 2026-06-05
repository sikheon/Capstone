import Table from "cli-table3";
import { ui } from "./ui.js";

export const COMMANDS = {};

function reg(name, meta) { COMMANDS[name] = meta; }

// ─────────── inspection (read-only, server-wide) ───────────

reg("/help", {
  args: "", help: "show this help",
  fn: async () => {
    const t = new Table({ head: ["command", "args", "help"], style: { head: ["cyan"] } });
    for (const k of Object.keys(COMMANDS).sort()) {
      const m = COMMANDS[k];
      t.push([k, m.args, m.help]);
    }
    console.log(t.toString());
  },
});

reg("/status",   { args: "", help: "FL server status",            fn: async (c) => ui.status(await c.api.status()) });
reg("/clients",  { args: "", help: "list connected clients",      fn: async (c) => ui.clients(await c.api.clients()) });
reg("/metrics",  { args: "", help: "per-round metrics",           fn: async (c) => ui.metrics(await c.api.metrics()) });
reg("/params",   { args: "", help: "current FL parameters",       fn: async (c) => ui.table(await c.api.params()) });
reg("/registry", { args: "", help: "available plug-ins on server",fn: async (c) => ui.registry(await c.api.registry()) });
reg("/rounds",   { args: "", help: "round history",               fn: async (c) => ui.table(await c.api.rounds()) });
reg("/whoami",   { args: "", help: "how this CLI is registered",  fn: async (c) => ui.table({ client_id: c.clientId, ...c.deviceInfo }) });

reg("/server", {
  args: "[url]", help: "show or change target FL server",
  fn: async (c, url) => {
    if (!url) return ui.info(`server: ${c.api.baseUrl}`);
    await c.setServer(url); ui.ok(`server → ${url}`);
  },
});

// ─────────── this CLI's local participation prefs ───────────

reg("/prefs", {
  args: "", help: "show this CLI's local preferences",
  fn: async (c) => ui.table(c.prefs ?? { algorithm: "fedavg", model: "cnn_mnist", dataset: "mnist", local_epochs: 1 }),
});

function setPref(key) {
  return async (c, v) => {
    if (!v) return ui.error(`usage: /${key} <name>  (see /registry for available)`);
    c.prefs = { ...(c.prefs ?? {}), [key]: v };
    ui.ok(`local ${key} → ${v}  (sent in next heartbeat)`);
  };
}

reg("/algorithm", { args: "<name>", help: "set my local algorithm preference", fn: setPref("algorithm") });
reg("/model",     { args: "<name>", help: "set my local model preference",     fn: setPref("model") });
reg("/dataset",   { args: "<name>", help: "set my local dataset preference",   fn: setPref("dataset") });
reg("/epochs",    { args: "<n>",    help: "set my local epochs per round",
  fn: async (c, n) => {
    const i = parseInt(n, 10);
    if (!Number.isFinite(i) || i <= 0) return ui.error("usage: /epochs <positive int>");
    c.prefs = { ...(c.prefs ?? {}), local_epochs: i };
    ui.ok(`local epochs → ${i}`);
  }});

// ─────────── participation lifecycle (this CLI only) ───────────

reg("/join", {
  args: "", help: "start heartbeating so the server counts me as ready",
  fn: async (c) => {
    if (c.heartbeatTimer) return ui.warn("already joined");
    const send = async () => {
      try {
        const flags = { client_id: c.clientId, kind: "cli", ...(c.prefs ?? {}) };
        await c.api._req("POST", "/api/heartbeat", flags);
      } catch (e) { ui.warn(`heartbeat failed: ${e.message || e}`); }
    };
    c.heartbeatTimer = setInterval(send, 5000);
    send();
    ui.ok("joined — heartbeating every 5s. /leave to stop");
  },
});

reg("/leave", {
  args: "", help: "stop heartbeating (server marks me inactive)",
  fn: async (c) => {
    if (!c.heartbeatTimer) return ui.warn("not currently joined");
    clearInterval(c.heartbeatTimer);
    c.heartbeatTimer = null;
    ui.ok("left — no further heartbeats");
  },
});

reg("/quit", { args: "", help: "exit", fn: () => process.exit(0) });

export async function dispatch(ctx, line) {
  line = (line || "").trim();
  if (!line) return;
  if (!line.startsWith("/")) {
    ui.warn(`unknown input '${line}' — commands start with /. try /help`);
    return;
  }
  const [name, ...args] = line.split(/\s+/);
  const meta = COMMANDS[name];
  if (!meta) { ui.error(`unknown command: ${name}`); return; }
  try { await meta.fn(ctx, ...args); }
  catch (e) { ui.error(`${name} failed: ${e.message || e}`); }
}
