const API_BASE = "http://localhost:8080/api/v1";

const setText = (id, value) => {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
};

const fetchJson = async (path) => {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders("GET"),
  });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json();
};

const postJson = async (path, payload) => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders("POST"),
    body: JSON.stringify(payload || {}),
  });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json();
};

const authHeaders = (method) => {
  const headers = { "Content-Type": "application/json" };
  const token = window.localStorage.getItem("tcp_admin_token");
  const csrf = window.localStorage.getItem("tcp_csrf_token");
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (method !== "GET" && csrf) {
    headers["X-TCP-CSRF-Token"] = csrf;
  }
  return headers;
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

const renderPaper = (payload) => {
  const exposure = payload.portfolio?.exposure || payload.exposure || {};
  setText("paper-gross", exposure.gross_exposure || "0");
  setText("paper-net", exposure.net_exposure || "0");
  setText("paper-hedge-ratio", exposure.hedge_ratio || "0");
  setText("paper-state", payload.panic_halted ? "halted" : "paper only");
};

const renderResearch = (payload) => {
  setText("feature-count", `${payload.features?.length || 0}`);
  setText("synthetic-count", `${payload.synthetic_ethbtc?.length || 0}`);
  setText("feature-source", payload.source || "local");
};

const renderBacktest = (payload) => {
  const report = payload.report || {};
  setText("backtest-fill-ratio", report.fill_ratio || "0");
  setText("backtest-maker-ratio", report.maker_taker_ratio || "0");
  setText("backtest-edge", report.expected_edge_after_costs || "0");
};

const renderStrategy = (payload) => {
  const output = document.getElementById("strategy-output");
  if (!output) {
    return;
  }
  const recommendations = payload.recommendations || [];
  const sessions = payload.sessions || [];
  const latest = sessions[sessions.length - 1];
  setText("strategy-state", latest ? latest.status : "inspection");
  output.textContent = JSON.stringify(
    {
      latest_session: latest || null,
      latest_recommendation: recommendations[recommendations.length - 1] || null,
    },
    null,
    2,
  );
};

const renderModels = (registry, evaluations, decisions) => {
  const latestModel = (registry.models || [])[0];
  const latestEvaluation = (evaluations.evaluations || [])[0];
  const latestDecision = (decisions.decisions || [])[0];
  setText("model-count", `${registry.models?.length || 0}`);
  setText(
    "model-state",
    latestModel ? latestModel.approval_state : "research_candidate",
  );
  setText(
    "model-edge",
    latestEvaluation ? latestEvaluation.expected_edge_after_costs : "0",
  );
  const output = document.getElementById("model-output");
  if (output) {
    output.textContent = JSON.stringify(
      {
        model: latestModel || null,
        evaluation: latestEvaluation || null,
        decision: latestDecision || null,
      },
      null,
      2,
    );
  }
};

const renderBinanceValidation = (payload) => {
  setText("testnet-state", payload.accepted ? "gated open" : "locked");
  setText("testnet-network", payload.network_calls || "not_performed");
  const output = document.getElementById("testnet-output");
  if (output) {
    output.textContent = JSON.stringify(
      {
        accepted: payload.accepted,
        reasons: payload.reasons,
        request_specs: payload.request_specs,
      },
      null,
      2,
    );
  }
};

const renderLiveReadonly = (payload) => {
  setText("live-readonly-state", payload.accepted ? "read only" : "locked");
  setText("live-order-state", payload.order_submission || "forbidden");
  const output = document.getElementById("live-readonly-output");
  if (output) {
    output.textContent = JSON.stringify(
      {
        accepted: payload.accepted,
        reasons: payload.reasons,
        credential_metadata: payload.credential_metadata,
        reconciliation: payload.snapshot?.reconciliation || null,
      },
      null,
      2,
    );
  }
};

const paperOrderPayload = () => {
  const form = document.getElementById("paper-order-form");
  const formData = new FormData(form);
  return Object.fromEntries(formData.entries());
};

const renderPaperResult = (payload) => {
  const output = document.getElementById("paper-result");
  if (output) {
    output.textContent = JSON.stringify(payload, null, 2);
  }
};

const bindPaperForm = () => {
  const form = document.getElementById("paper-order-form");
  const preview = document.getElementById("preview-paper-order");
  if (!form || !preview) {
    return;
  }
  preview.addEventListener("click", async () => {
    try {
      renderPaperResult(await postJson("/paper/preview", paperOrderPayload()));
    } catch (error) {
      renderPaperResult({ status: "error", reason: String(error) });
    }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      renderPaperResult(await postJson("/paper/orders", paperOrderPayload()));
      renderPaper(await fetchJson("/paper"));
      renderAudit(await fetchJson("/audit/records"));
    } catch (error) {
      renderPaperResult({ status: "error", reason: String(error) });
    }
  });
  const process = document.getElementById("process-paper-orders");
  if (process) {
    process.addEventListener("click", async () => {
      try {
        renderPaperResult(await postJson("/paper/process", {}));
        renderPaper(await fetchJson("/paper"));
      } catch (error) {
        renderPaperResult({ status: "error", reason: String(error) });
      }
    });
  }
};

const bindStrategyControls = () => {
  const actions = [
    ["start-strategy", "/strategy/sessions/start"],
    ["pause-strategy", "/strategy/sessions/pause"],
    ["stop-strategy", "/strategy/sessions/stop"],
  ];
  for (const [id, path] of actions) {
    const button = document.getElementById(id);
    if (!button) {
      continue;
    }
    button.addEventListener("click", async () => {
      try {
        const payload = await postJson(path, {});
        renderStrategy({
          sessions: payload.session ? [payload.session] : [],
          recommendations: payload.recommendations || [],
        });
      } catch (error) {
        renderStrategy({
          sessions: [],
          recommendations: [
            { action: "ERROR", explanation: String(error) },
          ],
        });
      }
    });
  }
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
      paper,
      research,
      backtest,
      strategy,
      modelRegistry,
      modelEvaluations,
      modelDecisions,
      testnetValidation,
      liveReadonly,
    ] = await Promise.all([
      fetchJson("/status"),
      fetchJson("/risk/status"),
      fetchJson("/control-surface"),
      fetchJson("/symbol-universe"),
      fetchJson("/account-state"),
      fetchJson("/symbol-metadata"),
      fetchJson("/fee-policy"),
      fetchJson("/audit/records"),
      fetchJson("/paper"),
      fetchJson("/research/features"),
      fetchJson("/backtests/report"),
      fetchJson("/strategy/sessions"),
      fetchJson("/models/registry"),
      fetchJson("/models/evaluations"),
      fetchJson("/models/decisions"),
      fetchJson("/binance/testnet/validation"),
      fetchJson("/live/readonly"),
    ]);
    renderStatus(status);
    renderRisk(risk);
    renderCommands(controlSurface);
    renderUniverse(universe);
    renderAccount(account);
    renderMetadata(metadata);
    renderFees(fees);
    renderAudit(audit);
    renderPaper(paper);
    renderResearch(research);
    renderBacktest(backtest);
    renderStrategy(strategy);
    renderModels(modelRegistry, modelEvaluations, modelDecisions);
    renderBinanceValidation(testnetValidation);
    renderLiveReadonly(liveReadonly);
  } catch (error) {
    setText("api-state", "offline");
  }
};

bindPaperForm();
bindStrategyControls();
boot();
