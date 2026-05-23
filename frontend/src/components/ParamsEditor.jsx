import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Input } from "@/components/ui/input.jsx";
import { Button } from "@/components/ui/button.jsx";
import { Switch } from "@/components/ui/switch.jsx";

const FIELDS = [
  ["total_rounds",         "int"],
  ["min_clients_per_round","int"],
  ["client_fraction",      "float"],
  ["round_timeout_sec",    "int"],
  ["local_epochs",         "int"],
  ["dropout_threshold",    "float"],
  ["auto_dropout_control", "bool"],
];

export default function ParamsEditor({ api, params, onSaved }) {
  const [form, setForm] = useState(params || {});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { setForm(params || {}); }, [params]);

  function update(k, type, raw) {
    let v = raw;
    if (type === "int")   v = raw === "" ? "" : parseInt(raw, 10);
    if (type === "float") v = raw === "" ? "" : parseFloat(raw);
    if (type === "bool")  v = Boolean(raw);
    setForm({ ...form, [k]: v });
  }

  async function save() {
    setBusy(true); setErr("");
    try {
      const patch = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v !== "" && v !== null && v !== undefined)
      );
      const saved = await api.patchParams(patch);
      onSaved?.(saved);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Parameters</CardTitle></CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-3">
          Admin-only · effective from the next round.
        </p>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {FIELDS.map(([k, type]) => (
            <label key={k} className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">{k}</span>
              {type === "bool" ? (
                <Switch checked={!!form[k]} onCheckedChange={(v) => update(k, type, v)} />
              ) : (
                <Input value={form[k] ?? ""} onChange={(e) => update(k, type, e.target.value)} />
              )}
            </label>
          ))}
        </div>
        <Button onClick={save} disabled={busy}>save</Button>
        {err && <div className="text-destructive text-sm mt-2">{err}</div>}
      </CardContent>
    </Card>
  );
}
