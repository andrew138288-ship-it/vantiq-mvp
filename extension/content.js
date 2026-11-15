// Read-only adapter for the currently open, user-visible WhatsApp Web conversation.
// Runs only after an explicit request from the VANTIQ side panel.
// Never accesses cookies, local storage, hidden APIs, contacts lists, or credentials.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "VANTIQ_READ_VISIBLE_CHAT") return false;

  const panel = document.querySelector('[data-testid="conversation-panel-messages"]');
  if (!panel) {
    sendResponse({ ok: false, error: "Open a WhatsApp conversation first." });
    return false;
  }

  const messageNodes = [...panel.querySelectorAll("[data-pre-plain-text]")].slice(-40);
  const lines = [];
  for (const node of messageNodes) {
    const text = [...node.querySelectorAll(".selectable-text")]
      .map((part) => part.innerText?.trim())
      .filter(Boolean)
      .join(" ");
    if (!text) continue;
    const direction = node.closest(".message-out") ? "Salesperson" : "Customer";
    lines.push(direction + ": " + text);
  }

  if (!lines.length) {
    sendResponse({ ok: false, error: "No readable text messages found in the currently loaded conversation." });
    return false;
  }
  sendResponse({ ok: true, transcript: lines.join("\n"), count: lines.length });
  return false;
});
