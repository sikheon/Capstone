import { useState } from "react";
import { Button } from "@/components/ui/button.jsx";
import { Badge } from "@/components/ui/badge.jsx";
import { Input } from "@/components/ui/input.jsx";

export default function Header({ server, onChangeServer, isAdmin, onLogin, onLogout, api }) {
  const [editingServer, setEditingServer] = useState(false);
  const [draft, setDraft] = useState(server);
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");

  function submitServer(e) {
    e.preventDefault();
    onChangeServer(draft.trim());
    setEditingServer(false);
  }

  async function submitLogin(e) {
    e.preventDefault();
    setErr("");
    try { await api.login(u, p); setU(""); setP(""); onLogin?.(); }
    catch (er) { setErr(String(er.message || er)); }
  }

  return (
    <header className="rounded-lg border bg-card shadow-sm px-6 py-4 flex items-center justify-between gap-6 flex-wrap">
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-primary text-2xl leading-none">⊛</span>
        <div>
          <div className="flex items-center gap-2 font-semibold text-foreground">
            FL Coordinator
            {isAdmin && <Badge>admin</Badge>}
          </div>
          <div className="text-xs text-muted-foreground">
            Capstone · 데굴데굴 · 군산대 SW
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 ml-auto flex-wrap">
        {/* Server URL */}
        <div className="flex items-center gap-2">
          {editingServer ? (
            <form onSubmit={submitServer} className="flex items-center gap-2">
              <Input value={draft} onChange={(e) => setDraft(e.target.value)} className="w-72 mono text-xs" autoFocus />
              <Button size="sm" type="submit">save</Button>
              <Button size="sm" variant="ghost" type="button"
                      onClick={() => { setDraft(server); setEditingServer(false); }}>cancel</Button>
            </form>
          ) : (
            <>
              <span className="text-xs text-muted-foreground">server</span>
              <code className="mono text-xs px-2 py-1 rounded bg-secondary text-primary">{server}</code>
              <Button size="sm" variant="outline" onClick={() => setEditingServer(true)}>change</Button>
            </>
          )}
        </div>

        {/* Admin auth */}
        {isAdmin ? (
          <Button size="sm" variant="ghost" onClick={onLogout}>logout</Button>
        ) : (
          <form onSubmit={submitLogin} className="flex items-center gap-2">
            <Input placeholder="admin user" value={u} onChange={(e) => setU(e.target.value)}
                   className="w-32 text-xs" />
            <Input placeholder="password" type="password" value={p} onChange={(e) => setP(e.target.value)}
                   className="w-32 text-xs" />
            <Button size="sm" type="submit">login</Button>
            {err && <span className="text-destructive text-xs">{err}</span>}
          </form>
        )}
      </div>
    </header>
  );
}
