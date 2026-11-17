# VANTIQ 2.0 — Customer Auto-Record & Customer Memory Specification

Status: approved product requirement; implementation pending.
Applies to: WhatsApp Web Chrome extension MVP and the VANTIQ backend.

## 1. Product decision

VANTIQ automatically identifies the customer in the currently open WhatsApp conversation, creates the customer record when a reliable identifier is available, and continuously maintains a complete, structured sales summary for that customer. Users do not manually create customer records.

This feature is customer memory for sales continuity, not bulk contact collection or a general-purpose CRM.

## 2. Identity and deduplication

- Scope every customer lookup and write to the authenticated tenant.
- Use a stable channel-scoped external identity, initially WhatsApp's visible conversation identifier where reliably available.
- Enforce a database uniqueness constraint on (tenant_id, channel, external_ref); do not rely on display name as an identity key.
- If identity is missing or ambiguous, do not create or merge a record automatically. Show an unresolved/needs-confirmation state and preserve strict separation from other customer contexts.
- Reopening the same conversation updates the existing customer and memory; it must not create duplicate customer rows.
- Never merge two records based only on matching names or inferred personal details.

## 3. Ingestion boundary

- For each analysis/update event, the extension may provide only the most recent 5 messages visibly rendered in the currently active conversation.
- No configurable message-count selector: the limit is fixed at 5.
- No hidden DOM/history traversal, background account ingestion, contact scraping, cookie/credential access, or cross-chat collection.
- A customer switch immediately clears the previous customer's in-memory transcript and cancels/invalidates outstanding analysis and memory-update responses. Every async result must be checked against the active conversation/customer identity before it is applied.
- Existing saved sales memory is a separate, tenant-scoped derived summary. It may be supplied as background context to a later analysis, but must never be represented as newly read WhatsApp history.

## 4. Automatically maintained sales summary

Maintain a structured, versioned summary with these sections where supported by evidence:

1. Customer identity and channel metadata (minimum necessary).
2. First-contact and last-contact timestamps.
3. Customer's stated needs, use case, and requirements.
4. Decision criteria and priorities (e.g. price, quality, delivery, reliability).
5. Budget or price expectations only when explicitly stated; retain currency and attribution.
6. Buying motivation and observed buying signals.
7. Objections, concerns, and unresolved questions.
8. Buying stage and evidence supporting the stage.
9. Strategies previously recommended or selected, plus recorded outcomes when known.
10. Confirmed commitments and next steps, with owner and due date only when explicit or user-approved.
11. Communication language/locale when reliably detected; preserve locale distinctions such as pt-BR vs pt-PT.
12. Unknowns, contradictions, and items requiring human confirmation.

Do not invent facts, budget, authority, purchase intent, timing, product specifications, stock, price, discounts, delivery dates, warranty, certifications, or commitments. Distinguish customer-stated facts, user-entered facts, AI inferences, and unknowns. Store confidence/provenance for extracted claims; label inferences as inferences.

## 5. Update behavior

- After an explicitly user-authorized analysis of the current 5-message window, extract only relevant new facts and reconcile them with the existing summary.
- Preserve prior facts unless new evidence supersedes them; retain unresolved contradictions rather than silently choosing one.
- Update last-contact time from a reliable message timestamp; do not fabricate a timestamp.
- Use an idempotency key for each source conversation/context version so retries cannot duplicate events or repeatedly inflate counts.
- Serialize or use optimistic version checks for concurrent updates. A stale analysis must not overwrite a newer summary.
- Save a new memory revision/audit event containing the changed fields, source conversation, source context version, timestamp, and model/version metadata. Do not store hidden/raw WhatsApp history as a substitute for the summary.
- If extraction or persistence fails, retain the previous valid summary and surface a recoverable status; never show a false "saved" success.

## 6. Customer controls and transparency

- Customer records are automatically created only when identity is reliable and within the active, authorized workflow.
- Users can view the current summary, see when it was last updated, inspect its provenance/uncertainties, and correct or delete saved customer memory.
- Provide a clear indication when automatic summary saving is active and when a save failed.
- Apply tenant isolation to customer records, memory revisions, and every related endpoint.
- Define retention/deletion behavior so deleting a customer also deletes or appropriately anonymizes associated memory and derived records according to the product's retention policy.

## 7. UI requirements

Customer workspace uses the approved VANTIQ 2.0 visual direction: Apple-inspired clean minimalism, professional/reliable/enterprise-grade; white, silver-gray, restrained blue accents; clear typography and compact information hierarchy.

The customer profile should show:
- Customer identity and channel.
- First/last contact.
- Current buying stage and evidence.
- Needs and decision criteria.
- Buying signals and objections.
- Complete sales summary with last-updated time.
- Historical summary revisions / changes.
- Recommended next action and any explicitly confirmed follow-up.
- Provenance and uncertainty labels.

Do not include a manual "Add customer" action. Do not include an auto-send action. AI replies remain editable and require the user to insert/copy and manually send.

## 8. Existing repository observations (2026-11-17)

- The current backend already has Customer, Conversation, Message, and CustomerMemory SQLAlchemy models.
- CustomerMemory currently stores one text summary per (tenant_id, customer_id) with a version and updated_at; it does not yet provide structured fields, revision history, provenance, idempotent update events, or automatic extraction/persistence workflow.
- The current customers API exposes manual POST /customers, list/get/patch endpoints. The manual create route must be removed from the user-facing product workflow or restricted to internal migration/admin use; the extension's automatic identification path needs a safe upsert/resolve endpoint.
- The current conversation message endpoint accepts authorized message payloads and allows a configurable API limit. The WhatsApp ingestion contract must enforce the fixed five-visible-message policy at the extension boundary and validate it server-side for the AI/memory workflow.
- The existing Customer.external_ref is not currently protected by a tenant+channel uniqueness constraint. Add an explicit channel identity model or equivalent unique constraint before enabling automatic customer creation.
- The current repository has an open React extension PR (#7) whose description includes configurable 5/10/15/20 message limits. This conflicts with the approved fixed-five requirement and must be reconciled before merge.
- This document is a product/engineering specification, not evidence that the feature is implemented.

## 9. Implementation sequence

P0 — identity safety and data model:
- Add channel-scoped external identity and tenant-scoped uniqueness.
- Add structured customer memory, revision/audit model, idempotency, and optimistic concurrency.
- Add safe resolve/upsert and memory read/update APIs with tenant checks.

P0 — authorized update pipeline:
- Enforce exactly 5 visible messages for the active WhatsApp conversation.
- Extract and reconcile only evidence from that authorized window.
- Persist versioned summary updates with provenance, confidence, and safe failure behavior.
- Add tests for deduplication, tenant isolation, cross-customer isolation, stale writes, retries, ambiguous identity, and no fabricated facts.

P0 — extension and UI:
- Remove manual customer creation from the normal user interface.
- Remove the message-count selector; always use 5.
- Display automatic record/save status and customer summary.
- Ensure B full right-side panel and C floating assistant never cover WhatsApp content or composer.
- Keep reply editing/copy/insertion user-controlled; never auto-send.

P1 — customer memory experience:
- Display summary revisions and changed facts.
- Improve next-step recommendations from the verified saved summary.
- Add user correction/deletion controls and retention handling.

## 10. Acceptance criteria

- Same tenant + same verified WhatsApp identity resolves to one customer record under concurrent requests.
- Different tenants never see or update one another's customers or memories.
- Ambiguous identity never causes an automatic merge.
- Every analysis/update uses exactly the current conversation's latest 5 visible messages; no hidden or other-chat content is read.
- Switching customers prevents prior customer data or late async results from entering the new customer's context.
- A successful save creates an auditable, versioned summary update; a failed save is never shown as successful.
- Customer summaries distinguish explicit facts, user-entered facts, AI inferences, and unknowns.
- Retries are idempotent and stale writes cannot overwrite newer memory.
- No automatic WhatsApp message sending is introduced.
- Automated tests and CI pass before the implementation PR is considered ready.
