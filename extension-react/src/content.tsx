import { createRoot } from "react-dom/client";
import App from "./App";
import styles from "./styles.css?inline";

const HOST_ID = "vantiq-sales-dock";

function readVisibleChat(limit: number): string {
  const panel = document.querySelector<HTMLElement>('[data-testid="conversation-panel-messages"]');
  if (!panel) throw new Error("请先在 WhatsApp Web 中打开一个客户对话。");

  const nodes = Array.from(panel.querySelectorAll<HTMLElement>("[data-pre-plain-text]")).slice(-limit);
  const lines: string[] = [];
  for (const node of nodes) {
    const text = Array.from(node.querySelectorAll<HTMLElement>(".selectable-text"))
      .map((part) => part.innerText?.trim())
      .filter(Boolean)
      .join(" ");
    if (!text) continue;
    const speaker = node.closest(".message-out") ? "Salesperson" : "Customer";
    lines.push(`${speaker}: ${text}`);
  }
  if (!lines.length) throw new Error("当前对话中没有找到可读取的可见文字消息。");
  return lines.join("\n");
}

function getConversationKey(): string {
  const header = document.querySelector<HTMLElement>('[data-testid="conversation-info-header"]');
  const title = header?.querySelector<HTMLElement>('span[title]')?.getAttribute("title");
  return title?.trim() || header?.getAttribute("aria-label")?.trim() || "";
}

function watchConversationSwitches() {
  let currentKey = getConversationKey();
  const observer = new MutationObserver(() => {
    const nextKey = getConversationKey();
    if (nextKey && currentKey && nextKey !== currentKey) {
      currentKey = nextKey;
      window.dispatchEvent(new Event("vantiq:conversation-changed"));
    } else if (nextKey && !currentKey) {
      currentKey = nextKey;
    }
  });
  if (document.body) observer.observe(document.body, { childList: true, subtree: true });
}

function mountDock() {
  if (document.getElementById(HOST_ID)) return;
  const host = document.createElement("div");
  host.id = HOST_ID;
  host.style.cssText = "all: initial; position: fixed; z-index: 2147483647; top: 0; right: 0; height: 100vh; width: 390px;";
  document.documentElement.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });
  const style = document.createElement("style");
  style.textContent = styles;
  const mountPoint = document.createElement("div");
  mountPoint.id = "vantiq-react-root";
  shadow.append(style, mountPoint);
  createRoot(mountPoint).render(<App onReadVisibleChat={readVisibleChat} />);
  watchConversationSwitches();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mountDock, { once: true });
} else {
  mountDock();
}
