import { readFileSync } from "node:fs";
import { FLApi } from "./api.js";
import { collectDeviceInfo } from "./device.js";
import { dispatch } from "./commands.js";
import { startRepl } from "./repl.js";
import { ui } from "./ui.js";

function parseArgs(argv) {
  const args = {
    server: process.env.FL_SERVER_URL || "http://localhost:8000",
    clientId: process.env.FL_CLIENT_ID || null,
    command: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--server")          args.server = argv[++i];
    else if (a === "--client-id")  args.clientId = argv[++i];
    else if (a === "-c" || a === "--command") args.command = argv[++i];
    else if (a === "-h" || a === "--help") {
      console.log("Usage: flctl [--server URL] [--client-id ID] [-c \"/cmd\"]");
      process.exit(0);
    } else if (a === "-v" || a === "--version") {
      const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
      console.log(pkg.version);
      process.exit(0);
    }
  }
  return args;
}

export async function main() {
  const args = parseArgs(process.argv.slice(2));
  const api = new FLApi(args.server);
  const info = collectDeviceInfo(args.clientId || "cli");

  try {
    const { client_id } = await api.provision(args.clientId);
    info.client_id = client_id;
    await api.register(info);
  } catch (e) {
    ui.warn(`setup failed: ${e.message || e}`);
  }

  const ctx = {
    api,
    clientId: info.client_id,
    deviceInfo: info,
    async setServer(url) {
      api.setBaseUrl(url);
      try {
        const { client_id } = await api.provision(this.clientId);
        info.client_id = client_id;
        this.clientId = client_id;
        await api.register(info);
      } catch (e) {
        ui.warn(`re-provision failed: ${e.message || e}`);
      }
    },
  };

  if (args.command) {
    await dispatch(ctx, args.command);
    return;
  }
  await startRepl(ctx);
}
