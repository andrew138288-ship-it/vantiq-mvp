const DEFAULT_API_URL = "https://vantiq-mvp-production.up.railway.app";
const apiInput = document.querySelector("#api-url");
const healthButton = document.querySelector("#health-check");
const status = document.querySelector("#status");
const loginSection = document.querySelector("#login-section");
const accountSection = document.querySelector("#account-section");
const loginForm = document.querySelector("#login-form");
const loginButton = document.querySelector("#login-button");
const authStatus = document.querySelector("#auth-status");
const accountName = document.querySelector("#account-name");
const customerList = document.querySelector("#customer-list");
const customerSelect = document.querySelector("#customer-select");
const analyzeButton = document.querySelector("#analyze");
const importChatButton = document.querySelector("#import-visible-chat");
const analysisStatus = document.querySelector("#analysis-status");
const decisionResult = document.querySelector("#decision-result");
const copyReplyButton = document.querySelector("#copy-reply");
let latestSuggestedReply = "";
const workspacePicker = document.querySelector("#workspace-picker");
const workspaceSelect = document.querySelector("#workspace-id");

function apiBase() {
  return apiInput.value.trim().replace(/\/+$/, "") || DEFAULT_API_URL;
}

async function apiRequest(path, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const apiPath = path === "/health" ? path : `/api/v1${path}`;
  const response = await fetch(`${apiBase()}${apiPath}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : body.detail?.message;
    const error = new Error(detail || `Request failed (HTTP ${response.status})`);
    error.status = response.status;
    error.detail = body.detail;
    throw error;
  }
  return body;
}

async function readSession() {
  const stored = await chrome.storage.session.get(["accessToken", "user"]);
  return stored.accessToken ? stored : null;
}

async function showSignedOut(message = "") {
  loginSection.hidden = false;
  accountSection.hidden = true;
  authStatus.textContent = message;
}

async function loadCustomers(token) {
  customerList.replaceChildren();
  customerSelect.replaceChildren(new Option("Select a customer", ""));
  const customers = await apiRequest("/customers?limit=50", {}, token);
  if (!customers.length) {
    const item = document.createElement("li");
    item.textContent = "No customers in this workspace yet. Add customers through the VANTIQ API first.";
    customerList.append(item);
    return;
  }
  for (const customer of customers) {
    const item = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = customer.display_name;
    item.append(name);
    customerList.append(item);
    customerSelect.add(new Option(customer.display_name, customer.id));
  }
}

async function restoreSession() {
  const session = await readSession();
  if (!session) return showSignedOut();
  try {
    const user = await apiRequest("/auth/me", {}, session.accessToken);
    accountName.textContent = `${user.display_name} · ${user.email} · ${user.role}`;
    loginSection.hidden = true;
    accountSection.hidden = false;
    await loadCustomers(session.accessToken);
  } catch {
    await chrome.storage.session.remove(["accessToken", "user"]);
    await showSignedOut("Your session expired. Please sign in again.");
  }
}

healthButton.addEventListener("click", async () => {
  status.textContent = "Checking…";
  healthButton.disabled = true;
  try {
    const data = await apiRequest("/health");
    status.textContent = data.status === "ok" ? "Connected to VANTIQ API." : "API responded with an unexpected status.";
  } catch (error) {
    status.textContent = `Backend unavailable: ${error.message}`;
  } finally {
    healthButton.disabled = false;
  }
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginButton.disabled = true;
  authStatus.textContent = "Signing in…";
  try {
    const credentials = {
      email: document.querySelector("#email").value.trim(),
      password: document.querySelector("#password").value,
      ...(workspaceSelect.value ? { tenant_id: workspaceSelect.value } : {}),
    };
    const result = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    await chrome.storage.session.set({ accessToken: result.access_token, user: result.user });
    document.querySelector("#password").value = "";
    await restoreSession();
  } catch (error) {
    if (error.status === 409 && error.detail?.code === "workspace_selection_required") {
      workspaceSelect.replaceChildren();
      for (const workspace of error.detail.workspaces || []) {
        const option = document.createElement("option");
        option.value = workspace.tenant_id;
        option.textContent = `${workspace.role} · ${workspace.tenant_id.slice(0, 8)}`;
        workspaceSelect.append(option);
      }
      workspacePicker.hidden = false;
      authStatus.textContent = "This account has multiple workspaces. Choose one and sign in again.";
    } else {
      authStatus.textContent = error.message;
    }
  } finally {
    loginButton.disabled = false;
  }
});

document.querySelector("#refresh-customers").addEventListener("click", async () => {
  const session = await readSession();
  if (!session) return restoreSession();
  try {
    await loadCustomers(session.accessToken);
  } catch (error) {
    authStatus.textContent = error.message;
  }
});

document.querySelector("#add-customer").addEventListener("click", async () => {
  const session = await readSession();
  const nameInput = document.querySelector("#new-customer-name");
  const displayName = nameInput.value.trim();
  if (!session) return showSignedOut("Please sign in again.");
  if (!displayName) {
    authStatus.textContent = "Enter a customer name.";
    return;
  }
  try {
    await apiRequest("/customers", {
      method: "POST",
      body: JSON.stringify({ display_name: displayName }),
    }, session.accessToken);
    nameInput.value = "";
    await loadCustomers(session.accessToken);
    authStatus.textContent = "Customer added.";
  } catch (error) {
    authStatus.textContent = error.message;
  }
});

document.querySelector("#logout").addEventListener("click", async () => {
  await chrome.storage.session.remove(["accessToken", "user"]);
  await showSignedOut("Signed out.");
});

apiInput.value = DEFAULT_API_URL;
restoreSession();

importChatButton.addEventListener("click", async () => {
  importChatButton.disabled = true;
  analysisStatus.textContent = "Requesting the currently open WhatsApp conversation…";
  try {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab?.id) throw new Error("No active browser tab found.");
    const result = await chrome.tabs.sendMessage(tab.id, { type: "VANTIQ_READ_VISIBLE_CHAT" });
    if (!result?.ok) throw new Error(result?.error || "Could not read the visible conversation.");
    document.querySelector("#transcript").value = result.transcript;
    analysisStatus.textContent = `Imported ${result.count} visible messages. Review the text and confirm authorization before analysis.`;
  } catch (error) {
    analysisStatus.textContent = error.message.includes("Receiving end does not exist")
      ? "Open WhatsApp Web and reload the tab, then try again."
      : error.message;
  } finally {
    importChatButton.disabled = false;
  }
});

analyzeButton.addEventListener("click", async () => {
  const session = await readSession();
  const customerId = customerSelect.value;
  const transcript = document.querySelector("#transcript").value.trim();
  const authorized = document.querySelector("#context-consent").checked;
  if (!session) return showSignedOut("Please sign in again.");
  if (!customerId) {
    analysisStatus.textContent = "Select a customer first.";
    return;
  }
  if (!transcript) {
    analysisStatus.textContent = "Paste the conversation context first.";
    return;
  }
  if (!authorized) {
    analysisStatus.textContent = "Confirm your authorization before sharing conversation context.";
    return;
  }

  analyzeButton.disabled = true;
  decisionResult.hidden = true;
  analysisStatus.textContent = "Creating an authorized conversation and analyzing…";
  try {
    const conversation = await apiRequest("/conversations", {
      method: "POST",
      body: JSON.stringify({ customer_id: customerId, channel: "whatsapp" }),
    }, session.accessToken);
    await apiRequest(`/conversations/${conversation.id}/authorize-context`, {
      method: "POST",
    }, session.accessToken);
    await apiRequest(`/conversations/${conversation.id}/messages`, {
      method: "POST",
      body: JSON.stringify({ direction: "inbound", body: transcript }),
    }, session.accessToken);
    const result = await apiRequest(`/conversations/${conversation.id}/sales-assist`, {
      method: "POST",
      body: JSON.stringify({
        response_locale: document.querySelector("#response-locale").value,
        sales_goal: document.querySelector("#sales-goal").value.trim() || null,
      }),
    }, session.accessToken);
    latestSuggestedReply = result.decision.suggested_reply;
    renderDecision(result.decision);
    copyReplyButton.hidden = false;
    analysisStatus.textContent = "Analysis complete. Review the draft before sending it yourself.";
  } catch (error) {
    analysisStatus.textContent = error.message;
  } finally {
    analyzeButton.disabled = false;
  }
});

function renderDecision(decision) {
  decisionResult.replaceChildren();
  const addSection = (heading, content) => {
    const section = document.createElement("section");
    const title = document.createElement("h3");
    title.textContent = heading;
    const body = document.createElement("p");
    body.textContent = content;
    section.append(title, body);
    decisionResult.append(section);
  };
  const addList = (heading, values) => {
    const section = document.createElement("section");
    const title = document.createElement("h3");
    title.textContent = heading;
    const list = document.createElement("ul");
    for (const value of values || []) {
      const item = document.createElement("li");
      item.textContent = value;
      list.append(item);
    }
    section.append(title, list);
    decisionResult.append(section);
  };
  const addStrategy = (heading, strategy) => {
    const section = document.createElement("section");
    const title = document.createElement("h3");
    title.textContent = heading + (strategy.name ? ` · ${strategy.name}` : "");
    section.append(title);
    for (const [label, value] of [
      ["Objective", strategy.objective], ["Rationale", strategy.rationale],
      ["Next move", strategy.next_move], ["Risk", strategy.risk],
    ]) {
      const p = document.createElement("p");
      p.textContent = `${label}: ${value}`;
      section.append(p);
    }
    decisionResult.append(section);
  };
  addSection("Customer situation", decision.customer_situation);
  addSection("Buying stage", decision.buying_stage);
  addList("Buying signals", decision.buying_signals);
  addList("Objections", decision.objections);
  addStrategy("Strategy 1", decision.strategy_1);
  addStrategy("Strategy 2", decision.strategy_2);
  addSection("Strategy comparison", decision.comparison);
  const selected = decision.selected_strategy === "strategy_1" ? decision.strategy_1 : decision.strategy_2;
  addSection("VANTIQ selected", `${selected.name}: ${decision.selection_reason}`);
  addSection("Suggested reply — review before sending", decision.suggested_reply);
  addList("Before sending", decision.before_sending);
  decisionResult.hidden = false;
}

copyReplyButton.addEventListener("click", async () => {
  if (!latestSuggestedReply) return;
  try {
    await navigator.clipboard.writeText(latestSuggestedReply);
    analysisStatus.textContent = "Suggested reply copied. Review it before manually sending.";
  } catch {
    analysisStatus.textContent = "Copy failed. Select and copy the reply text manually.";
  }
});
