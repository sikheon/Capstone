import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Badge } from "@/components/ui/badge.jsx";

export default function ServerStatus({ status }) {
  if (!status) {
    return (
      <Card>
        <CardHeader><CardTitle>Status</CardTitle></CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">loading…</div>
        </CardContent>
      </Card>
    );
  }

  const stateBadge = {
    running: <Badge variant="success">running</Badge>,
    paused:  <Badge variant="warning">paused</Badge>,
    stopped: <Badge variant="destructive">stopped</Badge>,
  }[status.orchestrator_state] ?? <Badge variant="outline">{status.orchestrator_state}</Badge>;

  const rows = [
    ["state",       stateBadge],
    ["algorithm",   <code className="mono text-primary">{status.algorithm}</code>],
    ["model",       <code className="mono text-primary">{status.model}</code>],
    ["dataset",     <code className="mono text-primary">{status.dataset}</code>],
    ["selection",   <code className="mono text-primary">{status.selection}</code>],
    ["dropout",     <code className="mono text-primary">{status.dropout_predictor}</code>],
    ["round",       <span className="mono">{status.round ?? "—"}</span>],
    ["history",     <span className="mono">{status.history_len}</span>],
    ["clients",     <span className="mono">{status.clients}</span>],
  ];

  return (
    <Card>
      <CardHeader><CardTitle>Server status</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-2 gap-y-2 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <div className="text-muted-foreground">{k}</div>
            <div>{v}</div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
