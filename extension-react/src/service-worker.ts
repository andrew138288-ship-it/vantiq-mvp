type ApiRequest = {
  type: "VANTIQ_API_REQUEST";
  path: string;
  method: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string;
};

const API_BASE = __VANTIQ_API_BASE__;

// The dock UI runs as a content script. Explicitly grant it access to the
// extension-scoped session store so the bearer token never enters page storage.
void chrome.storage.session.setAccessLevel({
  accessLevel: "TRUSTED_AND_UNTRUSTED_CONTEXTS",
});

chrome.runtime.onMessage.addListener((message: ApiRequest, sender, sendResponse) => {
  if (message?.type !== "VANTIQ_API_REQUEST") return false;

  if (!sender.url?.startsWith("https://web.whatsapp.com/")) {
    sendResponse({ ok: false, error: "拒绝来自非 WhatsApp Web 页面发起的请求。" });
    return false;
  }
  if (typeof message.path !== "string" || !message.path.startsWith("/") || message.path.includes("..") || message.path.includes("://")) {
    sendResponse({ ok: false, error: "API 路径无效。" });
    return false;
  }
  if (!["GET", "POST", "PATCH", "DELETE"].includes(message.method)) {
    sendResponse({ ok: false, error: "不支持的 API 请求方法。" });
    return false;
  }

  void (async () => {
    try {
      const apiPath = message.path === "/health" ? "/health" : `/api/v1${message.path}`;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (message.token) headers.Authorization = `Bearer ${message.token}`;
      const response = await fetch(`${API_BASE}${apiPath}`, {
        method: message.method,
        headers,
        ...(message.body === undefined ? {} : { body: JSON.stringify(message.body) }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof data.detail === "string"
          ? data.detail
          : (typeof data.detail?.message === "string" ? data.detail.message : "VANTIQ API 请求失败。");
        sendResponse({ ok: false, error: detail, status: response.status });
        return;
      }
      sendResponse({ ok: true, data });
    } catch {
      sendResponse({ ok: false, error: "无法连接后端。请确认本地 VANTIQ API 已启动。" });
    }
  })();
  return true;
});
