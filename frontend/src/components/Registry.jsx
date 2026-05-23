import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Button } from "@/components/ui/button.jsx";
import { Select } from "@/components/ui/select.jsx";

const KINDS = [
  ["algorithm", "algorithms"],
  ["model",     "models"],
  ["dataset",   "datasets"],
  ["selection", "selection"],
  ["dropout",   "dropout"],
];

export default function Registry({ api, registry, status, isAdmin, onSwap }) {
  const current = {
    algorithm: status?.algorithm,
    model: status?.model,
    dataset: status?.dataset,
    selection: status?.selection,
    dropout: status?.dropout_predictor,
  };
  return (
    <Card>
      <CardHeader><CardTitle>Pluggable modules</CardTitle></CardHeader>
      <CardContent>
        {!isAdmin && (
          <p className="text-sm text-muted-foreground mb-2">login as admin to swap.</p>
        )}
        <div className="flex flex-col gap-2">
          {KINDS.map(([kind, key]) => (
            <Row key={kind} api={api} kind={kind}
                 options={registry[key] || []}
                 current={current[kind]}
                 disabled={!isAdmin}
                 onSwap={onSwap} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function Row({ api, kind, options, current, disabled, onSwap }) {
  const [pick, setPick] = useState(current || options[0] || "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function go() {
    setBusy(true); setErr("");
    try { await api.swap(kind, pick); onSwap?.(); }
    catch (e) { setErr(String(e.message || e)); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid grid-cols-[100px_1fr_1fr_auto] gap-2 items-center">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{kind}</span>
      <code className="mono text-xs text-primary truncate">{current ?? "—"}</code>
      <Select value={pick} onChange={(e) => setPick(e.target.value)} disabled={disabled}>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </Select>
      <Button size="sm" variant="outline" onClick={go} disabled={disabled || busy || !pick}>
        swap
      </Button>
      {err && <span className="col-span-4 text-destructive text-xs">{err}</span>}
    </div>
  );
}
