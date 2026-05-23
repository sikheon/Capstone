import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Badge } from "@/components/ui/badge.jsx";
import { Button } from "@/components/ui/button.jsx";

const MODES = [
  { value: "sync",  label: "Sync",  hint: "round-based, wait for all selected" },
  { value: "async", label: "Async", hint: "continuous blend, MQTT-style" },
];

export default function SessionControl({ api, status, isAdmin, onChange }) {
  const [mode, setMode] = useState(status?.mode || "sync");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const state = status?.orchestrator_state || "stopped";
  const stateBadge = {
    running: <Badge variant="success">running</Badge>,
    paused:  <Badge variant="warning">paused</Badge>,
    stopped: <Badge variant="destructive">stopped</Badge>,
  }[state] ?? <Badge variant="outline">{state}</Badge>;

  async function call(fn) {
    setBusy(true); setErr("");
    try { await fn(); onChange?.(); }
    catch (e) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>FL session</CardTitle>
          <div className="flex items-center gap-2">
            {stateBadge}
            {status?.mode && <Badge variant="outline" className="mono">{status.mode}</Badge>}
            {status?.round != null && (
              <span className="text-xs text-muted-foreground mono">round {status.round}</span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!isAdmin && (
          <p className="text-sm text-muted-foreground">login as admin to control the session.</p>
        )}
        {isAdmin && (
          <>
            <div className="flex gap-2 mb-3">
              {MODES.map((m) => {
                const active = mode === m.value;
                const lock = state === "running" || state === "paused";
                return (
                  <button
                    key={m.value}
                    onClick={() => !lock && setMode(m.value)}
                    disabled={lock}
                    className={[
                      "flex-1 text-left rounded-md border px-3 py-2 transition-colors",
                      active ? "border-primary bg-primary/10" : "border-border hover:bg-secondary",
                      lock ? "opacity-50 cursor-not-allowed" : "",
                    ].join(" ")}
                  >
                    <div className="text-sm font-medium">{m.label}</div>
                    <div className="text-xs text-muted-foreground">{m.hint}</div>
                  </button>
                );
              })}
            </div>
            <div className="flex gap-2">
              <Button disabled={busy || state !== "stopped"} size="sm"
                      onClick={() => call(() => api.startRound(mode))}>Start</Button>
              <Button disabled={busy || state !== "running"} size="sm" variant="outline"
                      onClick={() => call(() => api.pauseRound())}>Pause</Button>
              <Button disabled={busy || state !== "paused"} size="sm" variant="outline"
                      onClick={() => call(() => api.resumeRound())}>Resume</Button>
              <Button disabled={busy || state === "stopped"} size="sm" variant="destructive"
                      onClick={() => call(() => api.stopRound())}>Stop</Button>
            </div>
          </>
        )}
        {err && <div className="text-destructive text-sm mt-2">{err}</div>}
      </CardContent>
    </Card>
  );
}
