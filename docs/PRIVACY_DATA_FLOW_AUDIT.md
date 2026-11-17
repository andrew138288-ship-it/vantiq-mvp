# VANTIQ — Privacy Data-Flow & Retention Audit (Engineering Snapshot)

**Status:** Internal engineering audit; not a legal opinion.  
**Reviewed branch:** `feat/react-whatsapp-dock`  
**Reviewed commit:** `25e42983ac64dbc3497b739af7adf48b7ae184ca`  
**Date:** 2026-11-16  
**Purpose:** Record what the current source code demonstrably handles, identify mismatches with the privacy draft, and block unsupported privacy promises.

## 1. Data categories visible in the current source

| Data | Current code evidence | Current handling |
|---|---|---|
| Account email, display name, password hash, account status, verification status, creation time | `User` model and auth routes | Stored in PostgreSQL; password stored as Argon2 hash |
| Verification and password-reset tokens | `EmailVerificationToken`, `PasswordResetToken` | Only SHA-256 token digest stored; raw one-time token sent by email; verification expiry 24h; reset expiry 30m |
| Refresh-session metadata | `RefreshSession` model and login/refresh routes | SHA-256 token digest stored; session/family IDs, created/last-used/expiry/revocation timestamps; user-agent truncated to 300 chars |
| Customer profile | `Customer` model and customer routes | Display name, external reference, preferred locale, free-text notes, timestamps stored in PostgreSQL |
| Conversation metadata | `Conversation` model | Tenant/customer relationship, channel, context version, authorization timestamp, active flag, creation time |
| Selected customer-message text | `Message` model and conversation routes | Message body and direction stored in PostgreSQL after explicit context authorization |
| Customer summary/memory | `CustomerMemory` model | Table/model exists; current read/write API usage and lifecycle were not established in this audit |
| AI request context | `routers/ai.py` and `services/ai_gateway.py` | Customer name, preferred locale, customer notes, message transcript, response locale and sales goal are sent to the configured OpenAI API |
| AI response | AI route | Returned to the extension; no persistent decision-history table was identified in the reviewed model |
| Email delivery data | `email.py` | SMTP sends account email and one-time verification/reset token; actual provider/location depends on deployment configuration |
| Extension session | React extension | Access and refresh tokens stored in `chrome.storage.session`; source sets session storage access level to trusted and untrusted extension contexts |

## 2. Important verified technical details

- The extension reads visible text from the currently open WhatsApp Web conversation only after the user invokes the read action. It selects the latest configured 5/10/15/20 visible message nodes.
- The extension clears local transcript/authorization/analysis state when it detects a conversation change. This relies on WhatsApp Web DOM selectors and must be validated against real sessions.
- The backend persists message bodies in the `messages` table. This is not merely transient in-memory processing.
- The AI route loads up to 40 stored messages for a conversation and sends a bounded context of up to 24,000 characters (including customer profile notes) to the configured OpenAI API.
- The configured model name in source defaults to `gpt-6-astra`; actual provider, model availability, processing region, retention terms and account configuration must be verified from deployment/provider settings. Do not infer data residency from the model name.
- The database stores refresh-token hashes rather than raw refresh tokens. Session user-agent is stored in truncated form.
- SMTP is not configured in source by default. Real email delivery and the SMTP provider's processing location remain unverified.
- Access token lifetime is 15 minutes; refresh-session lifetime is 30 days.

## 3. Material gaps and release blockers

### P0 — Message retention and context scope mismatch

The extension UI lets the user select 5/10/15/20 visible messages and creates a **new conversation record for each analysis attempt**, then posts only the selected latest messages to that record. Therefore the ordinary current UI flow does not accumulate prior batches into the same conversation. However, the backend sales-assist route independently queries up to 40 messages and does not receive an explicit selected-message batch ID or enforce the UI's 5/10/15/20 limit. Other API clients or future UI changes could therefore submit a larger context than the intended product setting.

**Required before pilot:** enforce the selected context limit server-side and bind analysis to the exact message batch/version authorized by the user. Add tests proving the server rejects or excludes messages outside that authorized batch. Preserve the current fresh-conversation-per-analysis isolation unless a deliberate product change is approved.

### P0 — Retention and deletion are not implemented as a complete lifecycle

The reviewed schema stores customer records, conversation records and message bodies, but this audit did not identify a complete user-facing deletion/export workflow or a documented automatic retention policy. No fixed retention period should be claimed.

**Required before pilot:** decide and implement deletion/retention for customer records, conversations, messages, customer memory, auth sessions, logs and backups; define account closure and data-request handling; test cascading deletion and backup expiry behavior.

### P0 — Third-party AI processing disclosure

Customer profile notes and stored conversation text are transmitted to the configured OpenAI API. The actual provider contract, account data controls, processing region, retention, subprocessors and any model-training settings were not verified from source.

**Required before pilot:** document the actual vendor/product configuration and data flow; review provider terms; minimize fields sent; provide appropriate notices and obtain any legally required permissions before processing third-party customer information.

### P0 — Mainland China data and AI regulatory assessment

The code alone cannot determine whether deployment and service operation trigger personal-information export, generative-AI service, algorithm filing, security assessment, licensing or other obligations.

**Required before public launch:** counsel-led assessment based on the actual operating entity, target users, hosting region, AI provider, product availability and actual service behavior. Do not state that a filing, approval or cross-border mechanism is complete unless evidenced.

### P1 — SMTP and logs

SMTP provider/location is not configured in source. Review production logging, error monitoring and infrastructure logs for email addresses, request bodies, authorization headers, message content and tokens. Ensure secrets and raw tokens are never logged.

### P1 — Consent is not implemented

The current registration form/backend request does not yet provide the required separate, unchecked acceptance of the Terms of Service and Privacy Notice, nor does the reviewed schema show durable versioned consent records. The legal documents remain drafts and must not be represented as approved or active.

## 4. Privacy notice drafting rules based on current evidence

The Privacy Notice draft may accurately say that selected chat text and customer profile information are stored and may be transmitted to the configured AI provider for analysis, subject to final provider verification. It must not claim:
- all data stays in mainland China;
- no cross-border transfer occurs;
- AI providers never retain or train on submitted data;
- chat content is automatically deleted after a fixed period;
- users can currently export/delete all data through a complete in-product workflow;
- all required Chinese regulatory filings, assessments or approvals have been completed.

## 5. Next engineering actions

1. Add an analysis-scoped context batch/version so the server receives only the messages explicitly selected for that analysis.
2. Add configurable retention/deletion jobs and account/customer data deletion workflows, with auditable tests.
3. Add a data inventory covering production database, backups, application logs, email provider, AI provider and hosting provider.
4. Implement separate Terms and Privacy acceptance only after approved document versions are supplied; persist document type, version, server timestamp and acceptance method.
5. Re-run CI and perform an end-to-end pilot test using synthetic customer data before any real customer conversations are processed.
