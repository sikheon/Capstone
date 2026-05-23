import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Badge } from "@/components/ui/badge.jsx";
import { Button } from "@/components/ui/button.jsx";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table.jsx";

export default function ClientsTable({ api, clients, isAdmin, onChange }) {
  async function kick(id)  { try { await api.kick(id);  onChange?.(); } catch (e) { alert(e.message); } }
  async function ban(id)   { try { await api.ban(id);   onChange?.(); } catch (e) { alert(e.message); } }
  async function unban(id) { try { await api.unban(id); onChange?.(); } catch (e) { alert(e.message); } }

  const now = Date.now() / 1000;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Connected clients ({clients.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>id</TableHead>
              <TableHead>kind</TableHead>
              <TableHead>hw</TableHead>
              <TableHead>os / arch</TableHead>
              <TableHead>net</TableHead>
              <TableHead>batt</TableHead>
              <TableHead>cpu</TableHead>
              <TableHead>risk</TableHead>
              <TableHead>last seen</TableHead>
              {isAdmin && <TableHead>actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {clients.map((c) => {
              const age = c.last_seen ? Math.max(0, Math.floor(now - c.last_seen)) : null;
              const batt = c.battery == null ? "—" : `${Math.round(c.battery*100)}%${c.charging ? "⚡" : ""}`;
              const cpu  = c.cpu_load == null ? "—" : `${Math.round(c.cpu_load*100)}%`;
              const risk = c.dropout?.risk ?? 0;
              const riskClass = risk >= 0.5 ? "text-destructive"
                              : risk >= 0.25 ? "text-warning"
                              : "text-success";
              return (
                <TableRow key={c.client_id} className={!c.active ? "opacity-40" : ""}>
                  <TableCell className="mono text-xs">
                    {c.client_id}{c.banned && <Badge variant="destructive" className="ml-2">banned</Badge>}
                  </TableCell>
                  <TableCell>{c.kind}</TableCell>
                  <TableCell title={c.model_hw} className="max-w-[200px] truncate">{c.model_hw || "—"}</TableCell>
                  <TableCell className="mono text-xs">{c.os || "—"} / {c.arch || "—"}</TableCell>
                  <TableCell>{c.network || "—"}</TableCell>
                  <TableCell className="mono">{batt}</TableCell>
                  <TableCell className="mono">{cpu}</TableCell>
                  <TableCell className={`mono ${riskClass}`}>{risk.toFixed(2)}</TableCell>
                  <TableCell className="mono text-xs text-muted-foreground">{age == null ? "—" : `${age}s`}</TableCell>
                  {isAdmin && (
                    <TableCell>
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline" onClick={() => kick(c.client_id)}>kick</Button>
                        {c.banned
                          ? <Button size="sm" variant="outline" onClick={() => unban(c.client_id)}>unban</Button>
                          : <Button size="sm" variant="destructive" onClick={() => ban(c.client_id)}>ban</Button>}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
