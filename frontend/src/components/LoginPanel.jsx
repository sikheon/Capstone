import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card.jsx";
import { Input } from "@/components/ui/input.jsx";
import { Button } from "@/components/ui/button.jsx";

export default function LoginPanel({ api, onLogin }) {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    setErr("");
    try {
      await api.login(u, p);
      onLogin();
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Admin login</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-3">
          Required to change parameters, swap modules, or kick / ban clients.
        </p>
        <form onSubmit={submit} className="flex gap-2">
          <Input placeholder="username" value={u} onChange={(e) => setU(e.target.value)} />
          <Input
            placeholder="password" type="password" value={p}
            onChange={(e) => setP(e.target.value)}
          />
          <Button type="submit">login</Button>
        </form>
        {err && <div className="text-destructive text-sm mt-2">{err}</div>}
      </CardContent>
    </Card>
  );
}
