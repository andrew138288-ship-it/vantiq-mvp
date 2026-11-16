import { useEffect, useState, type FormEvent } from "react";
import { parseTranscript } from "./transcript";

type Customer = { id: string; display_name: string };
type Session = { accessToken: string; refreshToken: string; user: { display_name?: string | null; email: string; role: string } };
type LoginResponse = { access_token: string; refresh_token: string; token_type: string; user: Session["user"] };
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
type ApiReply = { ok: boolean; data?: unknown; error?: string; status?: number };
type Props = { onReadVisibleChat: (limit: number) => string };
let refreshInFlight: Promise<Session | null> | null = null;

async function apiRequest<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
  token?: string,
): Promise<T> {
  const send = (requestPath: string, requestToken?: string, requestBody?: unknown) =>
    chrome.runtime.sendMessage({
      type: "VANTIQ_API_REQUEST",
      path: requestPath,
      method: options.method ?? "GET",
      body: requestBody,
      token: requestToken,
    }) as Promise<ApiReply>;
  let result = await send(path, token, options.body);
  if (!result?.ok && result.status === 401 && token && path !== "/auth/refresh") {
    const stored = await chrome.storage.session.get("vantiqSession");
    const saved = stored.vantiqSession as Session | undefined;
    if (saved?.accessToken && saved.accessToken !== token) {
      result = await send(path, saved.accessToken, options.body);
    } else if (saved?.refreshToken) {
      if (!refreshInFlight) {
        refreshInFlight = (async () => {
          const renewed = await chrome.runtime.sendMessage({
            type: "VANTIQ_API_REQUEST",
            path: "/auth/refresh",
            method: "POST",
            body: { refresh_token: saved.refreshToken },
          }) as ApiReply;
          if (!renewed?.ok || !renewed.data || typeof renewed.data !== "object") {
            await chrome.storage.session.remove("vantiqSession");
            window.dispatchEvent(new Event("vantiq:session-expired"));
            return null;
          }
          const tokens = renewed.data as { access_token: string; refresh_token: string };
          const updated = { ...saved, accessToken: tokens.access_token, refreshToken: tokens.refresh_token };
          await chrome.storage.session.set({ vantiqSession: updated });
          window.dispatchEvent(new CustomEvent("vantiq:session-refreshed", { detail: updated }));
          return updated;
        })();
      }
      let updated: Session | null = null;
      try { updated = await refreshInFlight; }
      finally { refreshInFlight = null; }
      if (updated) result = await send(path, updated.accessToken, options.body);
    }
  }
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
  const [confirmPassword, setConfirmPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [verificationToken, setVerificationToken] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register" | "verify" | "reset">("login");
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
  const [activeSessions, setActiveSessions] = useState<Array<{session_id:string;created_at:string;last_used_at:string|null;expires_at:string;device:string}>>([]);

  async function loadCustomers(token: string) {
    const result = await apiRequest<Customer[]>("/customers?limit=50", {}, token);
    setCustomers(result);
  }

  async function loadSessions(token: string) {
    const result = await apiRequest<Array<{session_id:string;created_at:string;last_used_at:string|null;expires_at:string;device:string}>>("/auth/sessions", {}, token);
    setActiveSessions(result);
  }

  async function revokeOneSession(sessionId: string) {
    if (!session) return;
    try {
      await apiRequest(`/auth/sessions/${sessionId}`, { method: "DELETE" }, session.accessToken);
      await loadSessions(session.accessToken);
      setAuthStatus("已撤销所选登录设备。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "撤销设备失败");
    }
  }

  async function revokeAllSessions() {
    if (!session) return;
    try {
      await apiRequest("/auth/logout-all", { method: "POST" }, session.accessToken);
      await chrome.storage.session.remove("vantiqSession");
      setSession(null);
      setCustomers([]);
      setActiveSessions([]);
      setCustomerId("");
      setDecision(null);
      setTranscript("");
      setAuthorized(false);
      setAuthStatus("所有设备已退出，请重新登录。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "退出所有设备失败");
    }
  }

  useEffect(() => {
    const handleConversationChange = () => {
      setTranscript("");
      setAuthorized(false);
      setDecision(null);
      setCustomerId("");
      setAnalysisStatus("检测到 WhatsApp 客户对话切换。旧对话已清空，请重新选择对应的 VANTIQ 客户。");
    };
    const handleSessionRefreshed = (event: Event) => setSession((event as CustomEvent<Session>).detail);
    const handleSessionExpired = () => { setSession(null); setCustomers([]); setAuthStatus("登录已过期，请重新登录。"); };
    window.addEventListener("vantiq:conversation-changed", handleConversationChange);
    window.addEventListener("vantiq:session-refreshed", handleSessionRefreshed);
    window.addEventListener("vantiq:session-expired", handleSessionExpired);
    return () => { window.removeEventListener("vantiq:conversation-changed", handleConversationChange); window.removeEventListener("vantiq:session-refreshed", handleSessionRefreshed); window.removeEventListener("vantiq:session-expired", handleSessionExpired); };
  }, []);

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
        const latest = await chrome.storage.session.get("vantiqSession");
        const active = (latest.vantiqSession as Session | undefined) || restored;
        setSession(active);
        await loadSessions(active.accessToken);
      } catch {
        await chrome.storage.session.remove("vantiqSession");
        setAuthStatus("登录状态已失效，请重新登录。");
      }
    })();
  }, []);

  async function registerAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password !== confirmPassword) {
      setAuthStatus("两次输入的密码不一致。");
      return;
    }
    setBusy(true);
    setAuthStatus("正在创建免费账户并发送验证邮件…");
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: { email: email.trim(), password, display_name: displayName.trim() },
      });
      setAuthMode("verify");
      setPassword("");
      setConfirmPassword("");
      setAuthStatus("如果该邮箱可以注册，验证邮件将发送至邮箱。请复制邮件中的一次性验证码。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "注册失败");
    } finally {
      setBusy(false);
    }
  }

  async function verifyAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setAuthStatus("正在验证邮箱…");
    try {
      await apiRequest("/auth/verify-email", {
        method: "POST",
        body: { token: verificationToken.trim() },
      });
      setAuthMode("login");
      setVerificationToken("");
      setAuthStatus("邮箱验证成功。免费账户已激活，请登录。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "邮箱验证失败");
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    if (!email.trim()) {
      setAuthStatus("请先输入注册邮箱。");
      return;
    }
    setBusy(true);
    try {
      await apiRequest("/auth/resend-verification", {
        method: "POST",
        body: { email: email.trim() },
      });
      setAuthStatus("如果该账户存在且仍需验证，新的验证邮件将发送至邮箱。旧验证码将失效。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "无法重新发送验证邮件");
    } finally {
      setBusy(false);
    }
  }

  async function requestPasswordReset() {
    if (!email.trim()) {
      setAuthStatus("请先输入注册邮箱。");
      return;
    }
    setBusy(true);
    try {
      await apiRequest("/auth/password-reset/request", {
        method: "POST",
        body: { email: email.trim() },
      });
      setAuthStatus("如果账户存在且已验证邮箱，密码重置说明将发送至邮箱。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "无法发送重置邮件");
    } finally {
      setBusy(false);
    }
  }

  async function confirmPasswordReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await apiRequest("/auth/password-reset/confirm", {
        method: "POST",
        body: { token: resetToken.trim(), new_password: newPassword },
      });
      setAuthMode("login");
      setResetToken("");
      setNewPassword("");
      setPassword("");
      setAuthStatus("密码已重置，请使用新密码登录。");
    } catch (error) {
      setAuthStatus(error instanceof Error ? error.message : "密码重置失败");
    } finally {
      setBusy(false);
    }
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setAuthStatus("正在登录…");
    try {
      const result = await apiRequest<LoginResponse>("/auth/login", {
        method: "POST",
        body: { email: email.trim(), password },
      });
      const restored: Session = { accessToken: result.access_token, refreshToken: result.refresh_token, user: result.user };
      await chrome.storage.session.set({ vantiqSession: restored });
      setSession(restored);
      setPassword("");
      await loadCustomers(restored.accessToken);
      await loadSessions(restored.accessToken);
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
      setTranscript("");
      setAuthorized(false);
      setDecision(null);
      setAnalysisStatus("客户已添加。请重新读取当前 WhatsApp 对话并确认授权后再分析。");
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
    if (session?.refreshToken) {
      try { await apiRequest("/auth/logout", { method: "POST", body: { refresh_token: session.refreshToken } }); } catch { /* local logout must still complete */ }
    }
    await chrome.storage.session.remove("vantiqSession");
    setSession(null);
    setCustomers([]);
    setActiveSessions([]);
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
        <section className="section">
          {authMode === "login" && (
            <form onSubmit={signIn}>
              <h2>登录账户</h2>
              <label htmlFor="vantiq-email">邮箱</label>
              <input id="vantiq-email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <label htmlFor="vantiq-password">密码</label>
              <input id="vantiq-password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <button className="primary full" disabled={busy}>{busy ? "请稍候…" : "登录 VANTIQ"}</button>
              <div className="inline-form">
                <button type="button" className="text-button" onClick={() => { setAuthMode("register"); setAuthStatus(""); }}>创建免费账户</button>
                <button type="button" className="text-button" onClick={() => { setAuthMode("verify"); setAuthStatus("请输入邮箱收到的一次性验证码。"); }}>验证邮箱</button>
                <button type="button" className="text-button" onClick={() => { setAuthMode("reset"); setAuthStatus(""); }}>忘记密码</button>
              </div>
            </form>
          )}
          {authMode === "register" && (
            <form onSubmit={registerAccount}>
              <h2>创建免费账户</h2>
              <label htmlFor="vantiq-name">姓名</label>
              <input id="vantiq-name" autoComplete="name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required maxLength={160} />
              <label htmlFor="vantiq-register-email">邮箱</label>
              <input id="vantiq-register-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <label htmlFor="vantiq-register-password">密码（至少 12 位）</label>
              <input id="vantiq-register-password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={12} maxLength={128} />
              <label htmlFor="vantiq-confirm-password">确认密码</label>
              <input id="vantiq-confirm-password" type="password" autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required minLength={12} maxLength={128} />
              <button className="primary full" disabled={busy}>{busy ? "正在提交…" : "注册免费账户"}</button>
              <button type="button" className="text-button" onClick={() => { setAuthMode("login"); setAuthStatus(""); }}>返回登录</button>
            </form>
          )}
          {authMode === "reset" && (
            <form onSubmit={confirmPasswordReset}>
              <h2>重置密码</h2>
              <label htmlFor="vantiq-reset-email">账户邮箱</label>
              <input id="vantiq-reset-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <button type="button" className="secondary full" onClick={requestPasswordReset} disabled={busy}>发送密码重置邮件</button>
              <label htmlFor="vantiq-reset-token">邮件中的一次性验证码</label>
              <input id="vantiq-reset-token" value={resetToken} onChange={(e) => setResetToken(e.target.value)} required minLength={32} maxLength={256} />
              <label htmlFor="vantiq-new-password">新密码（至少 12 位）</label>
              <input id="vantiq-new-password" type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={12} maxLength={128} />
              <button className="primary full" disabled={busy}>{busy ? "正在重置…" : "确认重置密码"}</button>
              <button type="button" className="text-button" onClick={() => { setAuthMode("login"); setAuthStatus(""); }}>返回登录</button>
            </form>
          )}
          {authMode === "verify" && (
            <form onSubmit={verifyAccount}>
              <h2>验证邮箱</h2>
              <p className="human-review">请打开注册邮箱，复制 VANTIQ 验证邮件中的一次性验证码。验证码 24 小时内有效，重新发送后旧验证码失效。</p>
              <label htmlFor="vantiq-verify-email">邮箱</label>
              <input id="vantiq-verify-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <label htmlFor="vantiq-verification-token">邮箱验证码</label>
              <input id="vantiq-verification-token" value={verificationToken} onChange={(e) => setVerificationToken(e.target.value)} required minLength={32} maxLength={256} />
              <button className="primary full" disabled={busy}>{busy ? "正在验证…" : "确认验证邮箱"}</button>
              <button type="button" className="secondary full" onClick={resendVerification} disabled={busy}>重新发送验证码</button>
              <button type="button" className="text-button" onClick={() => { setAuthMode("login"); setAuthStatus(""); }}>返回登录</button>
            </form>
          )}
          <p className="status" role="status">{authStatus}</p>
        </section>
      ) : (
        <>
          <section className="section account-row">
            <div><h2>工作区</h2><p>{session.user.display_name || session.user.email}</p></div>
            <button className="text-button" onClick={signOut}>退出</button>
          </section>

          <section className="section">
            <div className="account-row">
              <h2>登录设备</h2>
              <button className="text-button" onClick={() => void loadSessions(session.accessToken)}>刷新</button>
            </div>
            {activeSessions.length === 0 ? <p className="human-review">暂时没有可显示的有效登录设备。</p> : activeSessions.map((item) => (
              <div className="strategy" key={item.session_id}>
                <b>{item.device}</b>
                <p>登录时间：{new Date(item.created_at).toLocaleString()}</p>
                <p>有效至：{new Date(item.expires_at).toLocaleString()}</p>
                <button className="text-button" onClick={() => void revokeOneSession(item.session_id)}>退出此设备</button>
              </div>
            ))}
            <button className="secondary full" onClick={() => void revokeAllSessions()}>退出所有设备</button>
          </section>

          <section className="section">
            <h2>当前客户</h2>
            <p className="human-review">为防止把不同 WhatsApp 联系人的消息归到错误客户，请每次切换对话后手动确认对应客户。</p>
            <label htmlFor="vantiq-customer">选择客户</label>
            <select id="vantiq-customer" value={customerId} onChange={(e) => { setCustomerId(e.target.value); setTranscript(""); setAuthorized(false); setDecision(null); }}>
              <option value="">请选择并确认对应客户</option>
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
