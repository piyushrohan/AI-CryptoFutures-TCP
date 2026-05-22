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

const renderUniverse = (payload) => {
  const list = document.getElementById("universe-list");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  for (const instrument of payload.instruments || []) {
    const item = document.createElement("article");
    item.className = "command-item";
    const title = document.createElement("strong");
    title.textContent = instrument.symbol;
    const meta = document.createElement("span");
    meta.textContent = `${instrument.role} -> ${instrument.data_recording_level}`;
    const gate = document.createElement("span");
    gate.textContent = instrument.execution_enabled
      ? "execution candidate"
      : "not executable";
    item.append(title, meta, gate);
    list.appendChild(item);
  }
};

const renderAccount = (payload) => {
  const account = payload.account_state;
  const collateral = account.collateral_assets?.[0];
  setText("margin-mode", account.margin_mode);
  setText("position-mode", account.position_mode);
  setText("collateral-balance", collateral ? collateral.wallet_balance : "0");
  setText("maintenance-margin", account.maintenance_margin);
  setText("liquidation-distance", account.liquidation_distance_ratio);
  setText("funding-exposure", account.funding_exposure);
  setText(
    "account-freshness",
    account.freshness.is_stale ? "stale" : account.freshness.source,
  );
};

const renderMetadata = (payload) => {
  const list = document.getElementById("metadata-list");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  for (const symbol of payload.symbols || []) {
    const item = document.createElement("article");
    item.className = "command-item";
    const title = document.createElement("strong");
    title.textContent = symbol.symbol;
    const filters = symbol.filters || {};
    const meta = document.createElement("span");
    meta.textContent = `${symbol.contract_status} -> ${symbol.role}`;
    const detail = document.createElement("span");
    detail.textContent = symbol.is_executable
      ? `tick ${filters.tick_size}, lot ${filters.lot_size}, min notional ${filters.min_notional}`
      : "not executable";
    item.append(title, meta, detail);
    list.appendChild(item);
  }
  const stale = (payload.symbols || []).some((symbol) => symbol.freshness?.is_stale);
  setText("metadata-freshness", stale ? "stale" : "fresh");
};

const renderFees = (payload) => {
  const list = document.getElementById("fee-list");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  for (const policy of payload.fee_policies || []) {
    const item = document.createElement("article");
    item.className = "command-item";
    const title = document.createElement("strong");
    title.textContent = policy.symbol;
    const maker = document.createElement("span");
    maker.textContent = `maker ${policy.maker_fee_rate}`;
    const taker = document.createElement("span");
    taker.textContent = `taker ${policy.taker_fee_rate}`;
    item.append(title, maker, taker);
    list.appendChild(item);
  }
  const stale = (payload.fee_policies || []).some((policy) => {
    return policy.freshness?.is_stale;
  });
  setText("fee-freshness", stale ? "stale" : "fresh");
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
    const [
      status,
      risk,
      controlSurface,
      universe,
      account,
      metadata,
      fees,
      audit,
    ] = await Promise.all([
      fetchJson("/status"),
      fetchJson("/risk/status"),
      fetchJson("/control-surface"),
      fetchJson("/symbol-universe"),
      fetchJson("/account-state"),
      fetchJson("/symbol-metadata"),
      fetchJson("/fee-policy"),
      fetchJson("/audit/records"),
    ]);
    renderStatus(status);
    renderRisk(risk);
    renderCommands(controlSurface);
    renderUniverse(universe);
    renderAccount(account);
    renderMetadata(metadata);
    renderFees(fees);
    renderAudit(audit);
  } catch (error) {
    setText("api-state", "offline");
  }
};

boot();
