import chalk from "chalk";
import Table from "cli-table3";

const BANNER =
` ${chalk.cyan("┌─────────────────────────────────────┐")}
 ${chalk.cyan("│")}  ${chalk.bold.white("flctl")}  ${chalk.dim("federated learning control")}  ${chalk.cyan("│")}
 ${chalk.cyan("└─────────────────────────────────────┘")}`;

function ts() { return chalk.dim(new Date().toLocaleTimeString()); }

export const ui = {
  banner(server, version) {
    console.log(BANNER);
    console.log(`  ${chalk.dim("server")}  ${chalk.green(server)}   ${chalk.dim("v" + version)}`);
    console.log(`  type ${chalk.yellow("/help")} for commands, ${chalk.yellow("/quit")} to exit\n`);
  },
  info(msg)  { console.log(`${chalk.cyan("ℹ")} ${msg}`); },
  ok(msg)    { console.log(`${chalk.green("✓")} ${msg}`); },
  warn(msg)  { console.log(`${chalk.yellow("!")} ${msg}`); },
  error(msg) { console.log(`${chalk.red("✗")} ${msg}`); },

  status(s) {
    const t = new Table({ head: ["", ""], style: { head: ["cyan"] } });
    t.push(
      ["state",       chalk.bold(s.orchestrator_state || "?")],
      ["mode",        s.mode || "—"],
      ["algorithm",   chalk.green(s.algorithm)],
      ["model",       chalk.green(s.model)],
      ["dataset",     chalk.green(s.dataset)],
      ["selection",   chalk.green(s.selection)],
      ["dropout",     chalk.green(s.dropout_predictor || "—")],
      ["round",       String(s.round ?? "—")],
      ["history len", String(s.history_len)],
      ["clients",     String(s.clients)],
    );
    console.log(t.toString());
  },

  registry(r) {
    const t = new Table({ head: ["kind", "available"], style: { head: ["cyan"] } });
    for (const k of ["algorithms", "models", "datasets", "selection", "dropout"]) {
      t.push([k, (r[k] || []).join(", ")]);
    }
    console.log(t.toString());
  },

  clients(rows) {
    const t = new Table({
      head: ["id", "kind", "hw", "os/arch", "net", "batt", "cpu", "risk", "last", "ban"],
      style: { head: ["cyan"] },
      colWidths: [16, 8, 22, 16, 8, 8, 7, 8, 8, 5],
      wordWrap: true,
    });
    const now = Date.now() / 1000;
    for (const r of rows) {
      const age = r.last_seen ? `${Math.max(0, Math.floor(now - r.last_seen))}s` : "—";
      const batt = r.battery == null ? "—" :
        `${Math.round(r.battery * 100)}%${r.charging ? "⚡" : ""}`;
      const cpu = r.cpu_load == null ? "—" : `${Math.round(r.cpu_load * 100)}%`;
      const risk = r?.dropout?.risk ?? 0;
      const riskCell = risk >= 0.5 ? chalk.red(risk.toFixed(2))
        : risk >= 0.25 ? chalk.yellow(risk.toFixed(2)) : chalk.green(risk.toFixed(2));
      t.push([
        r.client_id, r.kind, (r.model_hw || "—").slice(0, 22),
        `${r.os || "?"}/${r.arch || "?"}`,
        r.network || "—", batt, cpu, riskCell, age,
        r.banned ? chalk.red("yes") : "",
      ]);
    }
    console.log(t.toString());
  },

  metrics(rows) {
    const t = new Table({
      head: ["round", "loss", "accuracy", "participants", "samples"],
      style: { head: ["cyan"] },
    });
    for (const r of rows) {
      t.push([
        r.round,
        (r.loss ?? 0).toFixed(4),
        (r.accuracy ?? 0).toFixed(4),
        r.participants ?? "—",
        r.samples ?? "—",
      ]);
    }
    console.log(t.toString());
  },

  table(obj) { console.log(JSON.stringify(obj, null, 2)); },

  ts,
};
