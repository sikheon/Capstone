import { useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Badge } from "@/components/ui/badge.jsx";

/** Highlights the project's headline value — dropout prediction — instead of
 *  leaving it as one column buried in the clients table.
 *
 *  Inputs:
 *    clients    : array from /api/clients (each has .dropout = {risk, reasons, predictor})
 *    predictor  : current predictor name (from status.dropout_predictor)
 */
export default function DropoutPanel({ clients, predictor }) {
  const { high, medium, safe, top3, predictorName, bands } = useMemo(() => {
    const active = (clients ?? []).filter((c) => c.active && !c.banned);
    const withRisk = active.map((c) => ({
      id: c.client_id,
      kind: c.kind,
      risk: c.dropout?.risk ?? 0,
      reasons: c.dropout?.reasons ?? [],
      batt: c.battery,
      charging: c.charging,
      net: c.network,
      cpu: c.cpu_load,
    }));
    const high   = withRisk.filter((c) => c.risk >= 0.5).length;
    const medium = withRisk.filter((c) => c.risk >= 0.25 && c.risk < 0.5).length;
    const safe   = withRisk.filter((c) => c.risk <  0.25).length;
    const top3   = [...withRisk].sort((a, b) => b.risk - a.risk).slice(0, 3);
    // 5-bucket histogram on [0,1]
    const bands = [0, 0, 0, 0, 0];
    for (const c of withRisk) {
      const idx = Math.min(4, Math.floor(c.risk * 5));
      bands[idx] += 1;
    }
    const predictorName = (clients ?? []).find((c) => c.dropout?.predictor)?.dropout?.predictor
                         ?? predictor ?? "rule_based";
    return { high, medium, safe, top3, predictorName, bands };
  }, [clients, predictor]);

  const total = high + medium + safe;
  const maxBand = Math.max(1, ...bands);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">이탈 위험 관리</CardTitle>
        <Badge variant="outline" className="mono text-[10px]">
          예측기 · {predictorName}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* risk bands */}
        <div className="grid grid-cols-3 gap-3">
          <RiskCell label="높음 (≥0.5)"   value={high}   tone="destructive" />
          <RiskCell label="중간 (0.25+)"  value={medium} tone="warning" />
          <RiskCell label="안전"          value={safe}   tone="success" />
        </div>

        {/* histogram */}
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5">
            위험 분포 (활성 {total}명)
          </div>
          <div className="flex items-end gap-1 h-12">
            {bands.map((n, i) => {
              const h = `${Math.round((n / maxBand) * 100)}%`;
              const tone = i >= 3 ? "bg-destructive/70"
                         : i >= 2 ? "bg-amber-500/70"
                         :          "bg-primary/40";
              return (
                <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
                  <div className={`${tone} w-full rounded-sm`} style={{ height: h, minHeight: n ? "4px" : "0" }} />
                  <span className="text-[9px] mono text-muted-foreground mt-0.5">{n}</span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[9px] text-muted-foreground mt-0.5 px-0.5">
            <span>0.0</span><span>0.2</span><span>0.4</span><span>0.6</span><span>0.8</span><span>1.0</span>
          </div>
        </div>

        {/* top-3 watchlist */}
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5">
            위험 상위 3명 · 자동 와치리스트
          </div>
          {top3.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">현재 활성 클라이언트 없음</p>
          ) : (
            <ul className="space-y-1.5">
              {top3.map((c) => (
                <li key={c.id} className="flex items-center gap-3 text-xs">
                  <span className="mono w-32 truncate">{c.id}</span>
                  <Badge variant="outline" className="text-[10px]">{c.kind}</Badge>
                  <RiskBar value={c.risk} />
                  <span className="mono w-10 text-right">{c.risk.toFixed(2)}</span>
                  <span className="text-muted-foreground truncate flex-1">
                    {c.reasons.length ? c.reasons.join(" · ") : "현재 위험 신호 없음"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function RiskCell({ label, value, tone }) {
  const color = tone === "destructive" ? "text-destructive"
              : tone === "warning"     ? "text-amber-600"
              : tone === "success"     ? "text-emerald-600"
              :                          "";
  return (
    <div className="rounded-md border bg-background px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={`text-2xl font-bold mono ${color}`}>{value}</div>
    </div>
  );
}

function RiskBar({ value }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const tone = value >= 0.5 ? "bg-destructive"
             : value >= 0.25 ? "bg-amber-500"
             : "bg-emerald-500";
  return (
    <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden max-w-[140px]">
      <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
