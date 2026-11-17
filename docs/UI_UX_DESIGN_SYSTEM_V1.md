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


## 8. Order capture and quote workspace (approved product requirement)

### User-approved configuration
- Price resolution combines a maintained product price list and customer-specific prices. Customer-specific pricing takes precedence when a valid matching rule exists; otherwise use the applicable product price-list rule.
- Quote persistence is manual: AI may prepare and populate a draft, but only the user can explicitly save it as a quote record.

### Primary flow
1. Detect a customer-stated order/request in the active, authorized conversation context. Capture product, quantity, unit, currency, requested date and relevant conditions only when explicitly supported.
2. Keep the detected request as a **customer order intent**, not a confirmed order or completed sale.
3. Resolve the product and applicable price in this order: valid customer-specific price rule; otherwise the matching product price-list rule. Historical prices mentioned in chat are not an automatic price source and must not override the configured price rules; they may only be considered after a future explicit product decision and user confirmation.
4. Price resolution must retain source, effective date/validity, currency, quantity tier, customer scope and confidence. If sources conflict, are expired, ambiguous, or missing, show “待確認價格”; never invent or silently choose a value.
5. Calculate line totals and quote totals only from confirmed quantities and resolved/explicitly approved unit prices. Keep tax, shipping, discounts, payment terms and validity as separate explicit fields; do not assume them.
6. Present an editable quote draft with a clear source trace for every resolved price. User reviews and edits it.
7. Only the explicit **手動保存報價單** action creates a persisted quote record. Show saved/failed state only after the backend confirms it.

### Quote status and transaction boundary
- Customer order intent → quote draft → manually saved quote.
- A saved quote is not an accepted order, paid invoice, shipment, revenue, or completed transaction.
- Never auto-send a quote or WhatsApp message. Sending/sharing remains a separate user action and is outside this manual-save requirement.
- Do not infer order acceptance from customer enthusiasm, an indicated quantity, or a request for a quote.
- Do not treat an old chat price as a current valid price without an applicable date/rule or user confirmation.

### Quote fields and provenance
- Customer identity (verified channel identity or explicitly confirmed customer).
- Product/SKU and description; quantity and unit; unit price and currency; line total.
- Price source: product price list or customer-specific price rule; include source reference and effective date/validity.
- Explicitly entered terms: discount, tax, shipping, payment terms, delivery terms, quote validity and notes.
- Quote number, creation time, creator, status, revision history and saved state.
- Missing or conflicting fields remain visibly unresolved; do not fill them with defaults that imply commercial agreement.

### Required UI states
- No order intent detected.
- Order intent detected; product or quantity needs confirmation.
- Product resolved; price matching in progress.
- Price matched with source and validity details.
- Price missing, expired, ambiguous or conflicting; manual review required.
- Editable draft; unsaved changes.
- Saving / saved / save failed (server-confirmed only).
- Conversation/customer changed; unsaved draft is isolated and must not carry over to another customer.

### Implementation boundary
The current MVP has no verified product-price catalog, customer price-rule resolver, or quote persistence API connected to the React dock. The first UI pass must therefore label these as pending integration and must not display sample prices as real data or claim a quote was saved. Implement the data contract and backend endpoints before enabling persistence.

## 9. Acceptance checklist additions

- [ ] Order quantity/product extraction is grounded in authorized visible conversation context and is editable for human correction.
- [ ] Order intent is not represented as an accepted/confirmed order.
- [ ] Price resolver supports product price lists and customer-specific prices, with customer-specific valid rules taking precedence.
- [ ] Every matched price exposes source, currency, scope, validity/effective date and quantity tier where applicable.
- [ ] Missing/conflicting/expired prices require human confirmation; no AI-invented price.
- [ ] Totals calculate only from confirmed quantities and resolved/approved prices.
- [ ] Quote terms are explicit; no assumed discount, tax, shipping, payment or delivery commitment.
- [ ] Quote draft is editable and isolated to the correct customer.
- [ ] Only an explicit user action saves a quote; saved state follows server confirmation.
- [ ] Saved quote is not mislabeled as accepted order, payment, shipment or revenue.
- [ ] No quote or WhatsApp message is automatically sent.

## 10. Acceptance checklist

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
