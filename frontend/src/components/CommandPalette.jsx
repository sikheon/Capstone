import { useEffect, useMemo, useRef, useState } from "react";

/** Claude-style slash command palette. Press `/` anywhere to open.
 *  Lists every admin / read-only action, filterable by typing. */
export default function CommandPalette({ api, isAdmin, status, registry, onChange, onLogin, onLogout }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("/");
  const [highlight, setHighlight] = useState(0);
  const [feedback, setFeedback] = useState("");
  const inputRef = useRef(null);

  const cmds = useMemo(() => buildCommands({ api, isAdmin, status, registry, onChange, onLogin, onLogout }), [api, isAdmin, status, registry]);

  const filtered = useMemo(() => {
    const head = query.toLowerCase();
    return cmds
      .filter((c) => c.name.toLowerCase().startsWith(head) || c.name.toLowerCase().includes(head.replace(/^\//, "")))
      .slice(0, 18);
  }, [cmds, query]);

  useEffect(() => {
    function onKey(e) {
      if (!open && e.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        setOpen(true);
        setQuery("/");
        setHighlight(0);
        setFeedback("");
      } else if (open) {
        if (e.key === "Escape") { setOpen(false); }
        else if (e.key === "ArrowDown") { e.preventDefault(); setHighlight((h) => Math.min(filtered.length - 1, h + 1)); }
        else if (e.key === "ArrowUp")   { e.preventDefault(); setHighlight((h) => Math.max(0, h - 1)); }
        else if (e.key === "Enter")     { e.preventDefault(); run(filtered[highlight]); }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, filtered, highlight]);

  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 10); }, [open]);

  async function run(cmd) {
    if (!cmd) return;
    if (cmd.admin && !isAdmin) { setFeedback("admin login required"); return; }
    try {
      await cmd.run();
      setFeedback(`✓ ${cmd.name} ok`);
      setTimeout(() => setOpen(false), 350);
    } catch (e) {
      setFeedback(`✗ ${cmd.name}: ${e.message || e}`);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => { setOpen(true); setQuery("/"); }}
        className="fixed bottom-5 right-5 z-40 rounded-full bg-primary text-primary-foreground shadow-lg px-4 py-2 text-sm font-medium hover:opacity-90"
        title="Press / for commands"
      >
        / commands
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-foreground/30 pt-[12vh]" onClick={() => setOpen(false)}>
      <div className="w-full max-w-xl rounded-lg border bg-popover text-popover-foreground shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="w-full px-4 py-3 bg-transparent text-sm mono outline-none border-b"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setHighlight(0); }}
          placeholder="type a slash command…"
        />
        <ul className="max-h-[60vh] overflow-y-auto py-1">
          {filtered.length === 0 && (
            <li className="px-4 py-3 text-sm text-muted-foreground">no match for {query}</li>
          )}
          {filtered.map((c, i) => (
            <li key={c.name}
                className={`px-4 py-2 cursor-pointer text-sm flex items-center gap-3 ${i === highlight ? "bg-primary/10" : "hover:bg-secondary"}`}
                onMouseEnter={() => setHighlight(i)}
                onClick={() => run(c)}>
              <span className="mono text-primary w-44 shrink-0">{c.name}</span>
              <span className="text-muted-foreground text-xs truncate">{c.help}</span>
              {c.admin && <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-destructive/10 text-destructive">admin</span>}
            </li>
          ))}
        </ul>
        {feedback && <div className="px-4 py-2 text-xs border-t text-muted-foreground">{feedback}</div>}
        <div className="px-4 py-2 text-[11px] text-muted-foreground border-t flex items-center justify-between">
          <span><kbd className="mono px-1 rounded bg-secondary">↑↓</kbd> navigate · <kbd className="mono px-1 rounded bg-secondary">⏎</kbd> run · <kbd className="mono px-1 rounded bg-secondary">esc</kbd> close</span>
          <span>{filtered.length} / {cmds.length}</span>
        </div>
      </div>
    </div>
  );
}

function buildCommands({ api, isAdmin, status, registry, onChange, onLogin, onLogout }) {
  const refresh = () => onChange?.();
  const out = [
    { name: "/status",   help: "show server status",       run: async () => { await api.status(); refresh(); } },
    { name: "/clients",  help: "list connected clients",   run: async () => { await api.clients(); refresh(); } },
    { name: "/metrics",  help: "round metrics",            run: async () => { await api.metrics(); refresh(); } },
    { name: "/registry", help: "list available plug-ins",  run: async () => { await api.registry(); refresh(); } },
    { name: "/params",   help: "show current parameters",  run: async () => { await api.params(); refresh(); } },

    { name: "/start sync",  admin: true, help: "start FL session (sync)",  run: async () => { await api.startRound("sync"); refresh(); } },
    { name: "/start async", admin: true, help: "start FL session (async)", run: async () => { await api.startRound("async"); refresh(); } },
    { name: "/pause",       admin: true, help: "pause the session",        run: async () => { await api.pauseRound(); refresh(); } },
    { name: "/resume",      admin: true, help: "resume the session",       run: async () => { await api.resumeRound(); refresh(); } },
    { name: "/stop",        admin: true, help: "stop the session",         run: async () => { await api.stopRound(); refresh(); } },

    { name: "/logout", admin: true, help: "admin logout", run: async () => { api.logout(); onLogout?.(); } },
  ];

  // dynamic swaps from registry
  const kinds = [
    ["algorithm", "algorithms"], ["model", "models"], ["dataset", "datasets"],
    ["selection", "selection"],  ["dropout", "dropout"],
  ];
  for (const [kind, key] of kinds) {
    for (const name of registry?.[key] || []) {
      out.push({
        name: `/${kind} ${name}`,
        admin: true,
        help: `swap ${kind} → ${name}`,
        run: async () => { await api.swap(kind, name); refresh(); },
      });
    }
  }

  return out;
}
