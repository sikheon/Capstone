import { cn } from "@/lib/utils.js";
import { Card } from "./card.jsx";

/** A compact KPI tile for the executive summary row.
 * Looks like Linear / GitHub Insights / Grafana stat cells. */
export function Kpi({ label, value, hint, accent = "default", className, mono = true }) {
  const accents = {
    default: "text-foreground",
    primary: "text-primary",
    success: "text-success",
    warning: "text-warning",
    destructive: "text-destructive",
    info: "text-info",
    muted: "text-muted-foreground",
  };
  return (
    <Card className={cn("px-4 py-3", className)}>
      <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "mt-1 text-2xl leading-tight font-semibold tabular-nums",
          mono && "mono",
          accents[accent],
        )}
      >
        {value}
      </div>
      {hint && (
        <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>
      )}
    </Card>
  );
}
