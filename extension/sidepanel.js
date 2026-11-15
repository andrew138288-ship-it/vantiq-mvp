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
const workspacePicker = document.querySelector("#workspace-picker");
const workspaceSelect = document.querySelector("#workspace-id");

function apiBase() {
  return apiInput.value.trim().replace(/\/+$/, "") || DEFAULT_API_URL;
}

async function apiRequest(path, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${apiBase()}${path}`, { ...options, headers });
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
  const customers = await apiRequest("/customers?limit=50", {}, token);
  if (!customers.length) {
    const item = document.createElement("li");
    item.textContent = "No customers in this workspace yet.";
    customerList.append(item);
    return;
  }
  for (const customer of customers) {
    const item = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = customer.display_name;
    item.append(name);
    if (customer.company) {
      const company = document.createElement("span");
      company.textContent = ` — ${customer.company}`;
      item.append(company);
    }
    customerList.append(item);
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

document.querySelector("#logout").addEventListener("click", async () => {
  await chrome.storage.session.remove(["accessToken", "user"]);
  await showSignedOut("Signed out.");
});

apiInput.value = DEFAULT_API_URL;
restoreSession();
