export class FLApi {
  constructor(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.adminToken = localStorage.getItem("fl.token") || null;
  }

  setServer(url) {
    this.baseUrl = url.replace(/\/+$/, "");
  }

  _adminHeaders() {
    return this.adminToken ? { Authorization: `Bearer ${this.adminToken}` } : {};
  }

  async _json(path, opts = {}) {
    const res = await fetch(this.baseUrl + path, {
      ...opts,
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText} — ${body}`);
    }
    return res.json();
  }

  // --- public ---
  status()   { return this._json("/api/status"); }
  registry() { return this._json("/api/registry"); }
  clients()  { return this._json("/api/clients"); }
  metrics()  { return this._json("/api/metrics"); }
  params()   { return this._json("/api/params"); }

  // --- admin ---
  async login(username, password) {
    const r = await this._json("/api/admin/login", {
      method: "POST", body: JSON.stringify({ username, password }),
    });
    this.adminToken = r.token;
    localStorage.setItem("fl.token", r.token);
    return r;
  }
  logout() {
    this.adminToken = null;
    localStorage.removeItem("fl.token");
  }
  isAdmin() { return Boolean(this.adminToken); }

  swap(kind, name) {
    return this._json(`/api/${kind}`, {
      method: "POST", headers: this._adminHeaders(),
      body: JSON.stringify({ name }),
    });
  }
  patchParams(patch) {
    return this._json("/api/params", {
      method: "PATCH", headers: this._adminHeaders(),
      body: JSON.stringify(patch),
    });
  }
  kick(id)   { return this._json(`/api/admin/kick/${id}`,  { method: "POST", headers: this._adminHeaders() }); }
  ban(id)    { return this._json(`/api/admin/ban/${id}`,   { method: "POST", headers: this._adminHeaders() }); }
  unban(id)  { return this._json(`/api/admin/unban/${id}`, { method: "POST", headers: this._adminHeaders() }); }
  banned()   { return this._json("/api/admin/banned",      { headers: this._adminHeaders() }); }

  startRound(mode = "sync") {
    return this._json("/api/admin/round/start", {
      method: "POST", headers: this._adminHeaders(),
      body: JSON.stringify({ mode }),
    });
  }

  // -------- benchmark --------
  benchmarkResults()       { return this._json("/api/benchmark/results"); }
  benchmarkGet(id)         { return this._json(`/api/benchmark/${id}`); }
  benchmarkRun(scenario)   {
    return this._json("/api/benchmark/run", {
      method: "POST", headers: this._adminHeaders(),
      body: JSON.stringify(scenario),
    });
  }
  benchmarkMatrix(matrix)  {
    return this._json("/api/benchmark/matrix", {
      method: "POST", headers: this._adminHeaders(),
      body: JSON.stringify(matrix),
    });
  }
  benchmarkDelete(id)      {
    return this._json(`/api/benchmark/${id}`, {
      method: "DELETE", headers: this._adminHeaders(),
    });
  }
  pauseRound()  { return this._json("/api/admin/round/pause",  { method: "POST", headers: this._adminHeaders() }); }
  resumeRound() { return this._json("/api/admin/round/resume", { method: "POST", headers: this._adminHeaders() }); }
  stopRound()   { return this._json("/api/admin/round/stop",   { method: "POST", headers: this._adminHeaders() }); }
  rounds()      { return this._json("/api/rounds"); }
}
