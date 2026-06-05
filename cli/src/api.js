export class FLApi {
  constructor(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.clientId = null;
    this.clientSecret = null;
    this.adminToken = null;
  }

  setBaseUrl(url) {
    this.baseUrl = url.replace(/\/+$/, "");
    this.adminToken = null; // tokens don't transfer between servers
  }

  _clientHeaders() {
    return this.clientId && this.clientSecret
      ? { "X-Client-Id": this.clientId, "X-Client-Secret": this.clientSecret }
      : {};
  }
  _adminHeaders() {
    return this.adminToken ? { Authorization: `Bearer ${this.adminToken}` } : {};
  }

  async _req(method, path, body = null, extraHeaders = {}) {
    const headers = { "Content-Type": "application/json", ...extraHeaders };
    const res = await fetch(this.baseUrl + path, {
      method,
      headers,
      body: body == null ? undefined : JSON.stringify(body),
    });
    const text = await res.text();
    if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${text}`);
    return text ? JSON.parse(text) : null;
  }

  // public
  status()   { return this._req("GET", "/api/status"); }
  registry() { return this._req("GET", "/api/registry"); }
  clients()  { return this._req("GET", "/api/clients"); }
  metrics()  { return this._req("GET", "/api/metrics"); }
  params()   { return this._req("GET", "/api/params"); }
  rounds()   { return this._req("GET", "/api/rounds"); }

  // client provisioning
  async provision(suggestedId = null) {
    const r = await this._req("POST", "/api/provision", { suggested_id: suggestedId });
    this.clientId = r.client_id;
    this.clientSecret = r.client_secret;
    return r;
  }
  register(payload) { return this._req("POST", "/api/register", payload, this._clientHeaders()); }

  // admin
  async login(username, password) {
    const r = await this._req("POST", "/api/admin/login", { username, password });
    this.adminToken = r.token;
    return r;
  }
  async logout() {
    if (!this.adminToken) return;
    await this._req("POST", "/api/admin/logout", null, this._adminHeaders());
    this.adminToken = null;
  }

  swap(kind, name)    { return this._req("POST", `/api/${kind}`, { name }, this._adminHeaders()); }
  patchParams(patch)  { return this._req("PATCH", "/api/params", patch, this._adminHeaders()); }
  startRound(mode)    { return this._req("POST", "/api/admin/round/start",  { mode }, this._adminHeaders()); }
  pauseRound()        { return this._req("POST", "/api/admin/round/pause",  null, this._adminHeaders()); }
  resumeRound()       { return this._req("POST", "/api/admin/round/resume", null, this._adminHeaders()); }
  stopRound()         { return this._req("POST", "/api/admin/round/stop",   null, this._adminHeaders()); }
  kick(id)            { return this._req("POST", `/api/admin/kick/${id}`,  null, this._adminHeaders()); }
  ban(id)             { return this._req("POST", `/api/admin/ban/${id}`,   null, this._adminHeaders()); }
  unban(id)           { return this._req("POST", `/api/admin/unban/${id}`, null, this._adminHeaders()); }
  banned()            { return this._req("GET",  "/api/admin/banned", null, this._adminHeaders()); }
}
