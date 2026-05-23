import { useEffect, useMemo, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Button } from "@/components/ui/button.jsx";
import { Input } from "@/components/ui/input.jsx";
import { Badge } from "@/components/ui/badge.jsx";
import { Switch } from "@/components/ui/switch.jsx";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table.jsx";

const CHART_COLORS = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)",
  "var(--chart-4)", "var(--chart-5)",
];

export default function BenchmarkPanel({ api, isAdmin, registry, tick }) {
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState([]);        // ids being compared
  const [detail, setDetail] = useState({});            // id → full result
  const [err, setErr] = useState("");

  // matrix form state
  const [name, setName] = useState("matrix-1");
  const [rounds, setRounds] = useState(15);
  const [numClients, setNumClients] = useState(8);
  const [iidAll, setIidAll] = useState(true);
  const [iidNon, setIidNon] = useState(true);
  const [drops, setDrops] = useState({ d0: true, d30: true, d50: true });
  const [sels, setSels] = useState({ all: true, random: false, dropout_aware: true });

  // refresh list
  useEffect(() => {
    let cancel = false;
    api.benchmarkResults()
      .then((d) => !cancel && setResults(d))
      .catch((e) => !cancel && setErr(String(e.message || e)));
    return () => { cancel = true; };
  }, [api, tick]);

  // load full detail for any newly-selected ids
  useEffect(() => {
    let cancel = false;
    Promise.all(
      selected.filter((id) => !detail[id])
              .map((id) => api.benchmarkGet(id).then((d) => [id, d])),
    ).then((pairs) => {
      if (cancel || !pairs.length) return;
      setDetail((d) => ({ ...d, ...Object.fromEntries(pairs) }));
    });
    return () => { cancel = true; };
  }, [selected, api]);

  async function runMatrix() {
    setErr("");
    const selectionOptions = Object.entries(sels).filter(([, v]) => v).map(([k]) => k);
    const iidOptions = [iidAll && true, iidNon && false].filter((v) => v !== undefined && v !== false || v === false);
    const finalIid = [];
    if (iidAll) finalIid.push(true);
    if (iidNon) finalIid.push(false);
    const dropList = [];
    if (drops.d0)  dropList.push(0.0);
    if (drops.d30) dropList.push(0.3);
    if (drops.d50) dropList.push(0.5);
    if (!selectionOptions.length || !finalIid.length || !dropList.length) {
      setErr("최소 하나의 selection · iid · dropout 옵션을 골라야 합니다."); return;
    }
    try {
      await api.benchmarkMatrix({
        base: { name, rounds, num_clients: numClients },
        selection_options: selectionOptions,
        iid_options: finalIid,
        dropout_rates: dropList,
      });
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  function toggle(id) {
    setSelected((cur) => cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]);
  }
  async function remove(id) {
    if (!confirm(`delete run ${id}?`)) return;
    try { await api.benchmarkDelete(id); } catch (e) { setErr(e.message); return; }
    setSelected((cur) => cur.filter((x) => x !== id));
    setDetail((cur) => { const c = { ...cur }; delete c[id]; return c; });
  }

  // chart data: { round: 0, "all/iid/d0": 0.88, ... }
  const chartData = useMemo(() => {
    const maxRounds = Math.max(0,
      ...selected.flatMap((id) => detail[id]?.rounds?.length ?? 0));
    const out = [];
    for (let r = 0; r < maxRounds; r++) {
      const row = { round: r };
      selected.forEach((id) => {
        const d = detail[id];
        if (!d) return;
        const cell = d.rounds[r];
        if (!cell) return;
        row[shortLabel(d)] = cell.test_accuracy;
      });
      out.push(row);
    }
    return out;
  }, [selected, detail]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Benchmark · scenario matrix</CardTitle>
          <Badge variant="outline" className="mono">{results.length} run(s)</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {!isAdmin && (
          <p className="text-sm text-muted-foreground mb-3">login as admin to launch new benchmarks.</p>
        )}
        {isAdmin && (
          <div className="rounded-md border border-border p-3 mb-4 grid grid-cols-2 gap-3 text-sm">
            <label className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">batch name</span>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <div className="flex gap-3">
              <label className="flex flex-col gap-1 flex-1">
                <span className="text-xs uppercase tracking-wider text-muted-foreground">rounds</span>
                <Input value={rounds} onChange={(e) => setRounds(+e.target.value)} />
              </label>
              <label className="flex flex-col gap-1 flex-1">
                <span className="text-xs uppercase tracking-wider text-muted-foreground">clients</span>
                <Input value={numClients} onChange={(e) => setNumClients(+e.target.value)} />
              </label>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">selection policies</div>
              <div className="flex gap-3 items-center text-xs">
                <ToggleChip label="all"           on={sels.all}            onChange={(v) => setSels({ ...sels, all: v })} />
                <ToggleChip label="random"        on={sels.random}         onChange={(v) => setSels({ ...sels, random: v })} />
                <ToggleChip label="dropout_aware" on={sels.dropout_aware}  onChange={(v) => setSels({ ...sels, dropout_aware: v })} />
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">data partition</div>
              <div className="flex gap-3 items-center text-xs">
                <ToggleChip label="IID"     on={iidAll} onChange={setIidAll} />
                <ToggleChip label="non-IID" on={iidNon} onChange={setIidNon} />
              </div>
            </div>

            <div className="col-span-2">
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">dropout rate (simulated)</div>
              <div className="flex gap-3 items-center text-xs">
                <ToggleChip label="0%"  on={drops.d0}  onChange={(v) => setDrops({ ...drops, d0:  v })} />
                <ToggleChip label="30%" on={drops.d30} onChange={(v) => setDrops({ ...drops, d30: v })} />
                <ToggleChip label="50%" on={drops.d50} onChange={(v) => setDrops({ ...drops, d50: v })} />
              </div>
            </div>

            <div className="col-span-2 flex items-center gap-3">
              <Button onClick={runMatrix}>run matrix</Button>
              <span className="text-xs text-muted-foreground">
                cross-product = {[Object.values(sels).filter(Boolean).length || 1,
                                 [iidAll, iidNon].filter(Boolean).length || 1,
                                 [drops.d0, drops.d30, drops.d50].filter(Boolean).length || 1]
                                 .reduce((a, b) => a * b, 1)} scenarios
              </span>
            </div>
          </div>
        )}

        {err && <div className="text-destructive text-sm mb-3">{err}</div>}

        {/* results table */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8"></TableHead>
              <TableHead>name</TableHead>
              <TableHead>algo</TableHead>
              <TableHead>selection</TableHead>
              <TableHead>iid</TableHead>
              <TableHead>drop</TableHead>
              <TableHead>rounds</TableHead>
              <TableHead>final acc</TableHead>
              <TableHead>final loss</TableHead>
              <TableHead>status</TableHead>
              {isAdmin && <TableHead></TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.length === 0 && (
              <TableRow>
                <TableCell colSpan={11} className="text-center text-muted-foreground py-6">
                  결과 없음 — 위에서 matrix 한 번 돌려보세요.
                </TableCell>
              </TableRow>
            )}
            {results.map((r) => {
              const on = selected.includes(r.id);
              const sc = r.scenario || {};
              return (
                <TableRow key={r.id} className={on ? "bg-primary/10" : ""}>
                  <TableCell>
                    <input type="checkbox" checked={on} onChange={() => toggle(r.id)} />
                  </TableCell>
                  <TableCell className="mono text-xs">{sc.name}</TableCell>
                  <TableCell className="mono text-xs">{sc.algorithm}</TableCell>
                  <TableCell className="mono text-xs">{sc.selection}</TableCell>
                  <TableCell className="mono text-xs">{sc.iid ? "IID" : "non-IID"}</TableCell>
                  <TableCell className="mono text-xs">{Math.round((sc.dropout_rate ?? 0) * 100)}%</TableCell>
                  <TableCell className="mono text-xs">{r.rounds}</TableCell>
                  <TableCell className="mono text-success">{(r.final_test_accuracy * 100).toFixed(2)}%</TableCell>
                  <TableCell className="mono text-warning">{r.final_test_loss.toFixed(4)}</TableCell>
                  <TableCell>
                    <Badge variant={r.status === "completed" ? "success" : r.status === "failed" ? "destructive" : "warning"}>
                      {r.status}
                    </Badge>
                  </TableCell>
                  {isAdmin && (
                    <TableCell>
                      <Button size="sm" variant="ghost" onClick={() => remove(r.id)}>×</Button>
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        {/* comparison chart */}
        {selected.length > 0 && chartData.length > 0 && (
          <div className="mt-4 w-full h-[300px]">
            <div className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
              accuracy comparison ({selected.length} run{selected.length > 1 ? "s" : ""})
            </div>
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="round" stroke="var(--muted-foreground)" tick={{ fontSize: 11 }} />
                <YAxis stroke="var(--muted-foreground)" tick={{ fontSize: 11 }} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{
                    background: "var(--popover)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)", fontSize: 12,
                  }}
                  formatter={(v) => (typeof v === "number" ? (v*100).toFixed(2) + "%" : v)}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {selected.map((id, i) => {
                  const d = detail[id];
                  return d ? (
                    <Line key={id}
                          type="monotone"
                          dataKey={shortLabel(d)}
                          stroke={CHART_COLORS[i % CHART_COLORS.length]}
                          dot={false}
                          isAnimationActive={false}
                          strokeWidth={2}/>
                  ) : null;
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function shortLabel(detail) {
  const s = detail.scenario || {};
  const sel = (s.selection || "?").replace("dropout_aware", "dropAware");
  const iid = s.iid ? "IID" : "nonIID";
  const drop = `${Math.round((s.dropout_rate || 0) * 100)}%`;
  return `${sel}/${iid}/${drop}`;
}

function ToggleChip({ label, on, onChange }) {
  return (
    <button
      onClick={() => onChange(!on)}
      className={[
        "px-2 py-1 rounded-md border text-xs transition-colors",
        on ? "border-primary bg-primary/15 text-primary"
           : "border-border hover:bg-secondary text-muted-foreground",
      ].join(" ")}
    >
      {label}
    </button>
  );
}
