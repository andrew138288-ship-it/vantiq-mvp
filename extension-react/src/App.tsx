import { useEffect, useState } from "react";
import { parseTranscript } from "./transcript";

type Customer = { id: string; display_name: string };
type Session = { accessToken: string; user: { display_name?: string; email: string; role: string } };
type Strategy = { name: string; objective: string; rationale: string; next_move: string; risk: string };
type Decision = {
  customer_situation: string;
  buying_stage: string;
  buying_signals: string[];
  objections: string[];
  strategy_1: Strategy;
  strategy_2: Strategy;
  comparison: string;
  selected_strategy: "strategy_1" | "strategy_2";
  selection_reason: string;
  suggested_reply: string;
  before_sending: string[];
};
type SalesAssistResponse = { decision: Decision; requires_human_review: boolean };
type ApiReply = { ok: boolean; data?: unknown; error?: string };
type Props = { onReadVisibleChat: (limit: number) => string };

async function apiRequest<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
  token?: string,
): Promise<T> {
  const result = await chrome.runtime.sendMessage({
    type: "VANTIQ_API_REQUEST",
    path,
    method: options.method ?? "GET",
    body: options.body,
    token,
  }) as ApiReply;
  if (!result?.ok) throw new Error(result?.error || "无法连接 VANTIQ 后端");
  return result.data as T;
}

function StrategyCard({ title, strategy, selected }: { title: string; strategy: Strategy; selected: boolean }) {
  return (
    <section className={selected ? "strategy selected" : "strategy"}>
      <div className="strategy-heading">
        <h3>{title} · {strategy.name}</h3>
        {selected && <span className="recommended">推荐</span>}
      </div>
      <p><b>目标：</b>{strategy.objective}</p>
      <p><b>依据：</b>{strategy.rationale}</p>
      <p><b>下一步：</b>{strategy.next_move}</p>
      <p><b>风险：</b>{strategy.risk}</p>
    </section>
  );
}

export default function App({ onReadVisibleChat }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authStatus, setAuthStatus] = useState("");
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [newCustomer, setNewCustomer] = useState("");
  const [transcript, setTranscript] = useState("");
  const [messageLimit, setMessageLimit] = useState(10);
  const [responseLocale, setResponseLocale] = useState("zh-CN");
  const [salesGoal, setSalesGoal] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState("");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadCustomers(token: string) {
    const result = await apiRequest<Customer[]>("/customers?limit=50", {}, token);
    setCustomers(result);
    if (!customerId && result[0]) setCustomerId(result[0].id);
  }

  useEffect(() => {
    void (async () => {
      const stored = await chrome.storage.session.get("vantiqSession");
      const saved = stored.vantiqSession as Session | undefined;
      if (!saved?.accessToken) return;
      try {
        const user = await apiRequest<Session["user"]>("/auth/me", {}, saved.accessToken);
        const restored = { ...saved, user };
        setSession(restored);
        await loadCustomers(saved.accessToken);
      } catch {
        await chrome.storage.session.remove("vantiqSession");
        setAuthStatus("登录状态已失效，请重新登录。");
      }
    })();
  }, []);

  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setAuthStatus("正在登录…");
    try {
      const result = await apiRequest<Session>("/auth/login", {
        method: "POST",
        body: { email: email.trim(), password },
      });
      await chrome.storage.session.set({ vantiqSession: result });
      setSession(result);
      setPassword("");
      await loadCustomers(result.accessToken);
      setAuthStatus("登录成功。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "登录失败");
    } finally {
      setBusy(false);
    }
  }

  async function addCustomer() {
    if (!session || !newCustomer.trim()) return;
    setBusy(true);
    try {
      const created = await apiRequest<Customer>("/customers", {
        method: "POST",
        body: { display_name: newCustomer.trim() },
      }, session.accessToken);
      setCustomers((current) => [...current, created]);
      setCustomerId(created.id);
      setNewCustomer("");
      setAuthStatus("客户已添加。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "添加客户失败");
    } finally {
      setBusy(false);
    }
  }

  function importVisibleChat() {
    try {
      const value = onReadVisibleChat(messageLimit);
      setTranscript(value);
      setAuthorized(false);
      setDecision(null);
      setAnalysisStatus(`已读取当前打开对话中的 ${parseTranscript(value).length} 条可见消息。请检查内容并明确授权后再分析。`);
    } catch (error) {
      setAnalysisStatus(error instanceof Error ? error.message : "读取对话失败");
    }
  }

  async function analyzeConversation() {
    if (!session) return;
    if (!customerId) return setAnalysisStatus("请先选择或添加客户。");
    if (!transcript.trim()) return setAnalysisStatus("请先读取或粘贴当前客户对话。");
    if (!authorized) return setAnalysisStatus("请先勾选授权确认。");
    const messages = parseTranscript(transcript);
    if (!messages.length) return setAnalysisStatus("没有可分析的有效消息。");

    setBusy(true);
    setDecision(null);
    setAnalysisStatus("正在授权当前对话并分析…");
    try {
      const conversation = await apiRequest<{ id: string }>("/conversations", {
        method: "POST",
        body: { customer_id: customerId, channel: "whatsapp" },
      }, session.accessToken);
      await apiRequest(`/conversations/${conversation.id}/authorize-context`, {
        method: "POST",
      }, session.accessToken);
      for (const message of messages.slice(-messageLimit)) {
        await apiRequest(`/conversations/${conversation.id}/messages`, {
          method: "POST",
          body: message,
        }, session.accessToken);
      }
      const result = await apiRequest<SalesAssistResponse>(
        `/conversations/${conversation.id}/sales-assist`,
        {
          method: "POST",
          body: { response_locale: responseLocale, sales_goal: salesGoal.trim() || null },
        },
        session.accessToken,
      );
      setDecision(result.decision);
      setAnalysisStatus("分析完成。请核对策略和回复，确认无误后由你手动发送。");
    } catch (error) {
      setAnalysisStatus(error instanceof Error ? error.message : "分析失败");
    } finally {
      setBusy(false);
    }
  }

  async function copyReply() {
    if (!decision?.suggested_reply) return;
    try {
      await navigator.clipboard.writeText(decision.suggested_reply);
      setAnalysisStatus("回复已复制。请检查后手动发送。");
    } catch {
      setAnalysisStatus("复制失败，请手动选择回复文本。");
    }
  }

  async function signOut() {
    await chrome.storage.session.remove("vantiqSession");
    setSession(null);
    setCustomers([]);
    setCustomerId("");
    setDecision(null);
    setTranscript("");
    setAuthorized(false);
    setAuthStatus("已退出登录。");
  }

  if (collapsed) {
    return <button className="collapsed-tab" onClick={() => setCollapsed(false)} aria-label="展开 VANTIQ">V</button>;
  }

  return (
    <aside className="dock">
      <header className="dock-header">
        <div>
          <span className="eyebrow">WORLD-CLASS SALES AI</span>
          <h1>VANTIQ</h1>
          <p>全球通用销售智慧</p>
        </div>
        <button className="icon-button" onClick={() => setCollapsed(true)} aria-label="收起面板">—</button>
      </header>

      <div className="safety-note">
        <strong>人工审核 · 不自动发送</strong>
        <span>只在你主动点击后读取当前打开的对话。</span>
      </div>

      {!session ? (
        <form className="section" onSubmit={signIn}>
          <h2>登录账户</h2>
          <label htmlFor="vantiq-email">邮箱</label>
          <input id="vantiq-email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <label htmlFor="vantiq-password">密码</label>
          <input id="vantiq-password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button className="primary" disabled={busy}>{busy ? "请稍候…" : "登录 VANTIQ"}</button>
          <p className="status" role="status">{authStatus}</p>
        </form>
      ) : (
        <>
          <section className="section account-row">
            <div><h2>工作区</h2><p>{session.user.display_name || session.user.email}</p></div>
            <button className="text-button" onClick={signOut}>退出</button>
          </section>

          <section className="section">
            <h2>当前客户</h2>
            <label htmlFor="vantiq-customer">选择客户</label>
            <select id="vantiq-customer" value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
              <option value="">请选择客户</option>
              {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}
            </select>
            <div className="inline-form">
              <input aria-label="新客户名称" placeholder="添加客户名称" value={newCustomer} onChange={(e) => setNewCustomer(e.target.value)} />
              <button className="secondary" onClick={addCustomer} disabled={busy || !newCustomer.trim()}>添加</button>
            </div>
          </section>

          <section className="section">
            <h2>读取当前对话</h2>
            <label htmlFor="vantiq-limit">读取最近可见消息</label>
            <select id="vantiq-limit" value={messageLimit} onChange={(e) => setMessageLimit(Number(e.target.value))}>
              {[5, 10, 15, 20].map((n) => <option key={n} value={n}>{n} 条</option>)}
            </select>
            <button className="secondary full" onClick={importVisibleChat}>读取当前 WhatsApp 对话</button>
            <label htmlFor="vantiq-transcript">对话内容（可检查和编辑）</label>
            <textarea id="vantiq-transcript" rows={7} value={transcript} onChange={(e) => setTranscript(e.target.value)} placeholder="点击上方按钮读取当前对话，或粘贴经授权的对话内容。" />
            <label className="consent">
              <input type="checkbox" checked={authorized} onChange={(e) => setAuthorized(e.target.checked)} />
              我确认有权将这段对话提供给 VANTIQ 分析。
            </label>
          </section>

          <section className="section">
            <h2>销售分析</h2>
            <label htmlFor="vantiq-locale">客户回复语言</label>
            <select id="vantiq-locale" value={responseLocale} onChange={(e) => setResponseLocale(e.target.value)}>
              <option value="zh-CN">简体中文</option>
              <option value="zh-TW">繁體中文</option>
              <option value="en-US">English (US)</option>
              <option value="pt-BR">Português (Brasil)</option>
              <option value="pt-PT">Português (Portugal)</option>
              <option value="es-ES">Español</option>
            </select>
            <label htmlFor="vantiq-goal">本次销售目标（可选）</label>
            <input id="vantiq-goal" value={salesGoal} onChange={(e) => setSalesGoal(e.target.value)} placeholder="例如：处理价格异议、推进成交" maxLength={500} />
            <button className="primary full" onClick={analyzeConversation} disabled={busy}>{busy ? "分析中…" : "分析对话并生成两种策略"}</button>
            <p className="status" role="status">{analysisStatus}</p>
          </section>

          {decision && (
            <section className="section results" aria-live="polite">
              <h2>客户情况</h2>
              <p>{decision.customer_situation}</p>
              <p><b>购买阶段：</b>{decision.buying_stage}</p>
              <h3>购买信号</h3><ul>{decision.buying_signals.map((item, i) => <li key={i}>{item}</li>)}</ul>
              <h3>客户异议</h3><ul>{decision.objections.map((item, i) => <li key={i}>{item}</li>)}</ul>
              <StrategyCard title="策略一" strategy={decision.strategy_1} selected={decision.selected_strategy === "strategy_1"} />
              <StrategyCard title="策略二" strategy={decision.strategy_2} selected={decision.selected_strategy === "strategy_2"} />
              <h3>策略比较</h3><p>{decision.comparison}</p>
              <div className="recommendation"><b>VANTIQ 推荐</b><p>{decision.selection_reason}</p></div>
              <h3>建议回复</h3>
              <div className="reply">{decision.suggested_reply}</div>
              <button className="secondary full" onClick={copyReply}>复制建议回复</button>
              <h3>发送前核实</h3><ul>{decision.before_sending.map((item, i) => <li key={i}>{item}</li>)}</ul>
              <p className="human-review">建议内容仅供审核，不会自动发送。</p>
            </section>
          )}
        </>
      )}
      <footer>VANTIQ · zh-CN 默认界面 · 用户手动决定是否发送</footer>
    </aside>
  );
}
