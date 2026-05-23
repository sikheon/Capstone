import { useEffect, useMemo, useState } from "react";
import { FLApi } from "./api/client.js";
import { connectEvents } from "./api/ws.js";
import { DEFAULT_SERVER, saveServer } from "./config.js";
import Header from "./components/Header.jsx";
import ServerStatus from "./components/ServerStatus.jsx";
import SessionControl from "./components/SessionControl.jsx";
import Registry from "./components/Registry.jsx";
import ParamsEditor from "./components/ParamsEditor.jsx";
import ClientsTable from "./components/ClientsTable.jsx";
import MetricsChart from "./components/MetricsChart.jsx";
import GlobalModelPanel from "./components/GlobalModelPanel.jsx";
import BenchmarkPanel from "./components/BenchmarkPanel.jsx";
import CommandPalette from "./components/CommandPalette.jsx";
import DropoutPanel from "./components/DropoutPanel.jsx";
import { Kpi } from "./components/ui/kpi.jsx";

export default function App() {
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER);
  const api = useMemo(() => new FLApi(serverUrl), [serverUrl]);
  const [tick, setTick] = useState(0);
  const [metrics, setMetrics] = useState([]);
  const [status, setStatus] = useState(null);
  const [registry, setRegistry] = useState({});
  const [params, setParams] = useState({});
  const [clients, setClients] = useState([]);
  const [globalModel, setGlobalModel] = useState(null);
  const [isAdmin, setIsAdmin] = useState(api.isAdmin());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, r, p, c, m, g] = await Promise.all([
          api.status(), api.registry(), api.params(), api.clients(), api.metrics(),
          api._json("/api/global_model").catch(() => null),
        ]);
        if (cancelled) return;
        setStatus(s); setRegistry(r); setParams(p); setClients(c); setMetrics(m);
        setGlobalModel(g);
      } catch (e) { console.error(e); }
    })();
    return () => { cancelled = true; };
  }, [api, tick]);

  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 3000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const stop = connectEvents(serverUrl, (event, payload) => {
      if (event === "round_finished" && payload?.metrics) {
        setMetrics((m) => [...m, { round: payload.round, ...payload.metrics }]);
      }
      if (event === "round_started" || event === "round_finished"
          || event === "async_update" || event === "global_eval") {
        setTick((n) => n + 1);
      }
    });
    return stop;
  }, [serverUrl]);

  function changeServer(url) {
    saveServer(url);
    setServerUrl(url);
  }

  const state = status?.orchestrator_state ?? "—";
  const stateAccent = state === "running" ? "success"
                    : state === "paused"  ? "warning"
                    : state === "stopped" ? "destructive"
                    : "muted";
  const cur = globalModel?.current;

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-[1440px] px-6 py-6 space-y-4">
        <Header
          server={serverUrl}
          onChangeServer={changeServer}
          isAdmin={isAdmin}
          api={api}
          onLogin={() => setIsAdmin(true)}
          onLogout={() => { api.logout(); setIsAdmin(false); }}
        />

        {/* KPI strip — 6 uniform cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <Kpi label="accuracy"
               value={cur ? `${(cur.test_accuracy*100).toFixed(2)}%` : "—"}
               hint={cur ? `r${cur.round} · n=${cur.test_samples}` : "no eval yet"}
               accent="success" />
          <Kpi label="loss"
               value={cur ? cur.test_loss.toFixed(4) : "—"}
               hint={globalModel ? `${globalModel.evaluated_count} evals` : ""}
               accent="warning" />
          <Kpi label="state" value={state} accent={stateAccent} mono={false} />
          <Kpi label="mode"  value={status?.mode ?? "—"} accent="primary" />
          <Kpi label="round" value={status?.round ?? "—"} />
          <Kpi label="clients" value={status?.clients ?? 0} />
        </div>

        {/* Dropout management — the headline value of this capstone */}
        <DropoutPanel clients={clients} predictor={status?.dropout_predictor} />

        {/* Row: big chart + global model panel — equal row height */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 auto-rows-fr">
          <div className="lg:col-span-2 h-full">
            <MetricsChart data={metrics} />
          </div>
          <div className="h-full">
            <GlobalModelPanel api={api} tick={tick} />
          </div>
        </div>

        {/* Row: Session control + Server status — equal height */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 auto-rows-fr">
          <div className="h-full">
            <SessionControl api={api} status={status} isAdmin={isAdmin}
                            onChange={() => setTick((n) => n + 1)} />
          </div>
          <div className="h-full">
            <ServerStatus status={status} />
          </div>
        </div>

        {/* Row: Modules + Params (params shown for everyone, locked when not admin) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 auto-rows-fr">
          <div className="h-full">
            <Registry api={api} registry={registry} status={status} isAdmin={isAdmin}
                      onSwap={() => setTick((n) => n + 1)} />
          </div>
          <div className="h-full">
            {isAdmin
              ? <ParamsEditor api={api} params={params} onSaved={(p) => setParams(p)} />
              : <LockedParams params={params} />}
          </div>
        </div>

        {/* Clients full width */}
        <ClientsTable api={api} clients={clients} isAdmin={isAdmin}
                      onChange={() => setTick((n) => n + 1)} />

        {/* Benchmark full width */}
        <BenchmarkPanel api={api} isAdmin={isAdmin} registry={registry} tick={tick} />
      </div>

      <CommandPalette
        api={api} isAdmin={isAdmin} status={status} registry={registry}
        onChange={() => setTick((n) => n + 1)}
        onLogin={() => setIsAdmin(true)}
        onLogout={() => { api.logout(); setIsAdmin(false); }}
      />
    </div>
  );
}

function LockedParams({ params }) {
  return (
    <div className="rounded-lg border bg-card shadow-sm px-5 py-4 h-full">
      <div className="text-[13px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
        Parameters
      </div>
      <p className="text-sm text-muted-foreground mb-3">admin login required to edit.</p>
      <div className="grid grid-cols-2 gap-y-1 text-xs">
        {Object.entries(params).map(([k, v]) => (
          <div key={k} className="contents">
            <span className="text-muted-foreground">{k}</span>
            <span className="mono">{String(v)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
