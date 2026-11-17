# VANTIQ UI/UX Foundation v1

Status: implementation baseline for the React WhatsApp Web extension; reviewable draft, not a production release.
Branch: feat/vantiq-ui-ux-foundation
Product direction: clean, restrained, Apple-inspired; white and cool-gray surfaces, measured blue accents, clear hierarchy, high legibility.

## 1. Product truth and data boundaries

WhatsApp is a conversation channel, not a transaction ledger. The interface must never imply that VANTIQ can read actual order value, revenue, paid amount, margin, or completed transaction status from WhatsApp chat alone.

### Conversation-derived information
- Customer-stated needs, requirements, use case, priorities, and constraints.
- Explicitly stated budget or price expectations, retaining currency and attribution.
- Questions, objections, concerns, buying signals, and unresolved issues.
- Conversation-supported buying stage, clearly labeled as an AI assessment.
- Language/locale, including pt-BR and pt-PT as distinct locales.
- Confirmed next steps and commitments only when explicitly present.

### Not inferable from chat alone
- Actual transaction amount, order value, revenue, margin, payment, refund, invoice, inventory, or shipment status.
- A completed purchase merely because the customer sounds interested or says they will buy.
- A budget or target price that the customer has not stated.

If transaction metrics are later required, they must be supplied by explicit user entry or a separately connected, authorized order/commerce/ERP source. Show source and last-synced time. If no source exists, omit the metric or show “尚未連接交易資料”; never show a guessed zero.

## 2. Information architecture

The primary experience is a focused sales workspace, not a general CRM.

1. **Conversation context** — current WhatsApp contact/conversation, source boundary, visible-message preview and explicit analysis action.
2. **Customer intelligence** — needs, priorities, buying signals, objections, buying-stage assessment, language, open questions.
3. **Strategy decision** — exactly two materially different strategies, side-by-side comparison, VANTIQ recommendation and rationale.
4. **Reply workspace** — editable proposed reply, copy/insert action, pre-send verification. Sending remains manual in WhatsApp.
5. **Customer memory** — concise structured sales summary, provenance/confidence, last-updated time, revision history and correction controls.
6. **Account & privacy** — account, active sessions, export and privacy controls; secondary to the sales workflow.

## 3. Primary workflow

1. User opens a WhatsApp conversation.
2. VANTIQ resolves the active customer only when a reliable channel identifier is available. Ambiguous identity stays unresolved; do not create or merge a record from display name alone.
3. User explicitly requests analysis. The extension reads exactly the latest five visibly rendered messages in that active conversation; no hidden history traversal or cross-chat ingestion.
4. User reviews the visible context and confirms authorization.
5. VANTIQ returns customer situation, buying-stage assessment, signals, objections, exactly two strategies, recommendation, editable reply and pre-send checks.
6. User edits/copies/inserts the reply and manually sends it.
7. VANTIQ updates customer memory only through the authorized summary workflow. Display saved/failed state accurately.

## 4. Core UI components

- **Dock header:** VANTIQ identity, current mode and collapse control.
- **Active conversation strip:** verified contact identity or “需要確認身份”; never silently substitute a different customer.
- **Context boundary note:** “僅分析目前對話最近 5 條可見訊息；不讀取其他聊天紀錄。”
- **Analysis action:** explicit, disabled until identity/context/authorization requirements are met.
- **Customer intelligence cards:** needs, decision criteria, signals, objections, buying stage and unknowns. Every inference is labeled.
- **Strategy comparison:** two clearly differentiated options; recommendation badge appears only on the selected recommendation.
- **Reply editor:** editable text, copy action and pre-send checklist; no auto-send.
- **Memory panel:** facts grouped by customer-stated, user-entered and AI-inferred; show provenance and update status.
- **Empty/error/loading states:** explain what is missing and give a safe recovery action. Never show success optimistically.

## 5. Visual system

- Canvas: white / very light cool gray; cards white with subtle neutral borders.
- Accent: restrained deep blue for primary actions and focus.
- Text: high-contrast charcoal; secondary metadata in accessible slate.
- Radius: consistent modest rounding; avoid excessive pill controls.
- Spacing: compact but breathable; keep primary sales actions above account settings.
- Typography: system sans-serif with robust Chinese fallback; clear 12/14/16/20/24px hierarchy.
- Motion: minimal, short and nonessential; respect reduced-motion preferences.
- Focus: visible keyboard focus; semantic headings, labels and live status regions.
- Responsive: dock must not obscure WhatsApp conversation or message composer. Reserve actual layout space where supported; if space cannot be safely reserved at a narrow viewport, collapse to a non-obstructive launcher rather than cover chat controls.

## 6. Required states

- Signed out / login / registration / verification / password reset.
- Signed in, no active conversation.
- Active conversation with verified identity.
- Active conversation with ambiguous/unavailable identity.
- Context not yet read; context loaded; user editing context.
- Authorization required / authorized / authorization revoked on conversation switch.
- Analysis in progress / completed / failed / stale response discarded.
- Memory not yet available / saved / save failed / conflicting facts.
- Two strategies returned / recommendation rationale / reply edited / copied.
- Narrow viewport / dock collapsed.

## 7. UX corrections required against current React dock

The current React implementation in the parent branch has several known mismatches:
- Customer must be manually selected or manually added; this conflicts with the approved automatic reliable-identity workflow.
- The message-count selector allows 5/10/15/20; the product requirement fixes the limit at exactly five.
- The dock is fixed-position and may cover WhatsApp content; responsive non-obstruction is not yet proven.
- Customer memory, provenance and revision history are not integrated into the visible customer workspace.
- The screen gives account/session/export controls substantial prominence ahead of the core sales workflow.

These are recorded as implementation work, not claimed as fixed by this document.

## 8. Acceptance checklist

- [ ] Exactly five latest visibly rendered messages are the only WhatsApp context used.
- [ ] No manual “Add customer” workflow in normal product UI.
- [ ] Reliable identity auto-resolves; ambiguous identity fails closed.
- [ ] Conversation switch clears old context and discards late responses.
- [ ] No transaction/revenue/order metrics are inferred from WhatsApp messages.
- [ ] Any external transaction metric has an explicit source, authorization and freshness indicator.
- [ ] Exactly two distinct strategies are shown with one recommendation and rationale.
- [ ] Replies remain editable and manually sent by the user.
- [ ] Customer memory shows provenance, uncertainty, saved status and revision history.
- [ ] Dock does not obscure WhatsApp chat or composer at supported widths.
- [ ] Keyboard, focus, contrast, loading, empty and error states are verified.
- [ ] Automated tests and a manual WhatsApp Web visual check pass before merge.
