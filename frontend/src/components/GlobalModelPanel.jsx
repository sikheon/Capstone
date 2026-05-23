import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";

export default function GlobalModelPanel({ api, tick }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancel = false;
    api._json("/api/global_model")
      .then((d) => !cancel && setData(d))
      .catch((e) => !cancel && setErr(String(e.message || e)));
    return () => { cancel = true; };
  }, [api, tick]);

  const cur = data?.current;
  const hist = data?.history || [];

  return (
    <Card>
      <CardHeader><CardTitle>Global model · held-out test set</CardTitle></CardHeader>
      <CardContent>
        {err && <div className="text-destructive text-sm mb-3">{err}</div>}
        {!cur ? (
          <div className="text-sm text-muted-foreground">
            평가 결과 없음 — 라운드가 한 번 완료되거나 async 모드에서 N개의 update가 들어오면 갱신됨.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <Row k="round" v={<code className="mono">{cur.round ?? "—"}</code>} />
            <Row k="model" v={<code className="mono text-primary">{cur.model}</code>} />
            <Row k="test loss" v={<span className="mono text-warning">{cur.test_loss?.toFixed(4)}</span>} />
            <Row k="test accuracy"
                 v={<span className="mono text-success">{(cur.test_accuracy*100).toFixed(2)}%</span>} />
            <Row k="test samples" v={<span className="mono">{cur.test_samples}</span>} />
            <Row k="evals" v={<span className="mono">{data.evaluated_count}</span>} />
            <Row k="last eval"
                 v={<span className="mono text-xs">{new Date(cur.evaluated_at*1000).toLocaleTimeString()}</span>} />
            <Row k="duration" v={<span className="mono text-xs">{cur.eval_duration_sec?.toFixed(2)}s</span>} />
          </div>
        )}
        {hist.length >= 2 && (
          <details className="mt-3 text-sm">
            <summary className="text-muted-foreground cursor-pointer">
              history ({hist.length})
            </summary>
            <div className="mt-2 max-h-48 overflow-y-auto border border-border rounded-md">
              <table className="w-full text-xs">
                <thead className="bg-secondary/40">
                  <tr>
                    <th className="text-left px-2 py-1 text-muted-foreground font-medium">round</th>
                    <th className="text-left px-2 py-1 text-muted-foreground font-medium">loss</th>
                    <th className="text-left px-2 py-1 text-muted-foreground font-medium">accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {hist.slice(-50).reverse().map((h, i) => (
                    <tr key={i} className="border-t border-border/60">
                      <td className="px-2 py-1 mono">{h.round ?? "—"}</td>
                      <td className="px-2 py-1 mono text-warning">{h.test_loss?.toFixed(4)}</td>
                      <td className="px-2 py-1 mono text-success">{(h.test_accuracy*100).toFixed(2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        )}
      </CardContent>
    </Card>
  );
}

function Row({ k, v }) {
  return (
    <div className="contents">
      <div className="text-muted-foreground">{k}</div>
      <div>{v}</div>
    </div>
  );
}
