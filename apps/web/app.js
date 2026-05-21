const API_BASE = "http://localhost:8080";

const setText = (id, value) => {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
};

const fetchJson = async (path) => {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json();
};

const renderStatus = (payload) => {
  const runtime = payload.runtime;
  setText("api-state", "connected");
  setText("operator-mode", runtime.operator_mode);
  setText("venue-target", runtime.venue_target);
  setText("credential-scope", runtime.credential_scope);
  setText("trading-gate", runtime.trading_gate);
  setText("autonomy-stage", runtime.autonomy_stage);
  setText("live-trading", runtime.live_trading_enabled ? "enabled" : "disabled");
};

const renderRisk = (payload) => {
  setText("risk-state", payload.fail_closed ? "fail closed" : "open");
  const list = document.getElementById("risk-guardrails");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  for (const item of payload.guardrails || []) {
    const row = document.createElement("li");
    row.textContent = item;
    list.appendChild(row);
  }
};

const renderCommands = (payload) => {
  const list = document.getElementById("command-list");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  for (const command of payload.commands || []) {
    const item = document.createElement("article");
    item.className = "command-item";
    const title = document.createElement("strong");
    title.textContent = command.operator_action;
    const meta = document.createElement("span");
    meta.textContent = `${command.screen} -> ${command.command_type}`;
    const gate = document.createElement("span");
    gate.textContent = command.execution_available
      ? "read-only available"
      : "future gated";
    item.append(title, meta, gate);
    list.appendChild(item);
  }
};

const renderAudit = (payload) => {
  const records = payload.records || [];
  setText("audit-count", `${records.length} records`);
  const container = document.getElementById("audit-records");
  if (!container) {
    return;
  }
  if (records.length === 0) {
    container.textContent = "No command decisions yet.";
    return;
  }
  container.textContent = records
    .slice(-3)
    .map((record) => `${record.record_id}: ${record.command_type} ${record.decision}`)
    .join("\n");
};

const boot = async () => {
  try {
    const [status, risk, controlSurface, audit] = await Promise.all([
      fetchJson("/status"),
      fetchJson("/risk/status"),
      fetchJson("/control-surface"),
      fetchJson("/audit/records"),
    ]);
    renderStatus(status);
    renderRisk(risk);
    renderCommands(controlSurface);
    renderAudit(audit);
  } catch (error) {
    setText("api-state", "offline");
  }
};

boot();
