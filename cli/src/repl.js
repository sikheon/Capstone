import readline from "node:readline";
import chalk from "chalk";
import { COMMANDS, dispatch } from "./commands.js";
import { ui } from "./ui.js";
import { readFileSync } from "node:fs";

const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));

export async function startRepl(ctx) {
  ui.banner(ctx.api.baseUrl, pkg.version);
  ui.ok(`registered as ${ctx.clientId}`);
  ui.info(`type ${chalk.cyan("/")} to see commands · ${chalk.cyan("/help")} for full list`);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    completer: (line) => {
      if (!line.startsWith("/")) return [[], line];
      const head = line.split(" ")[0];
      const matches = Object.keys(COMMANDS).filter((c) => c.startsWith(head));
      return [matches, head];
    },
    historySize: 1000,
    terminal: true,
  });

  function setPrompt() {
    const tag = ctx.heartbeatTimer ? chalk.green("flctl·joined") : chalk.cyan("flctl");
    rl.setPrompt(`${tag} ${chalk.green("›")} `);
  }
  setPrompt();
  rl.prompt();

  // ---------- /menu: Claude-style inline suggestion list ----------
  let menuLines = 0; // how many lines we drew below the prompt

  function clearMenu() {
    if (menuLines === 0) return;
    // save current column (cursor is on the prompt line; we want to wipe lines below)
    process.stdout.write("\x1B[s"); // save cursor
    readline.moveCursor(process.stdout, 0, 1);
    readline.cursorTo(process.stdout, 0);
    readline.clearScreenDown(process.stdout);
    process.stdout.write("\x1B[u"); // restore cursor
    menuLines = 0;
  }

  function renderMenu(buffer) {
    clearMenu();
    if (!buffer || !buffer.startsWith("/")) return;
    const head = buffer.split(" ")[0];
    const matches = Object.entries(COMMANDS)
      .filter(([k]) => k.startsWith(head))
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(0, 14);
    if (!matches.length) {
      // show a "no match" hint
      process.stdout.write("\x1B[s");
      process.stdout.write("\n  " + chalk.gray("no command matches ") + chalk.yellow(head));
      process.stdout.write("\x1B[u");
      menuLines = 2;
      return;
    }
    // longest name for column alignment
    const w = Math.max(...matches.map(([k]) => k.length));
    process.stdout.write("\x1B[s");
    process.stdout.write("\n");
    menuLines = 1;
    for (const [name, meta] of matches) {
      const pad = " ".repeat(w - name.length);
      const lock = meta.admin ? chalk.red("admin") : chalk.gray("    ·");
      const args = meta.args ? chalk.gray(" " + meta.args) : "";
      process.stdout.write(
        `  ${chalk.cyan(name)}${pad}${args}   ${lock}  ${chalk.gray(meta.help)}\n`
      );
      menuLines += 1;
    }
    process.stdout.write("\x1B[u");
  }

  // keypress fires AFTER readline updates its line buffer
  process.stdin.on("keypress", (_ch, key) => {
    // skip when readline is dispatching (Enter) — handled by rl.on('line')
    if (key && (key.name === "return" || key.name === "enter")) return;
    setImmediate(() => renderMenu(rl.line));
  });

  rl.on("line", async (line) => {
    clearMenu();
    await dispatch(ctx, line);
    setPrompt();
    rl.prompt();
  });

  rl.on("close", () => {
    clearMenu();
    ui.info("bye");
    process.exit(0);
  });
}
