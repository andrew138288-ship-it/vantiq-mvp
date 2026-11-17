# Legal Consent Implementation Specification

> Status: DRAFT — engineering requirements only. This is not legal advice and does not publish or approve the Terms of Service or Privacy Notice. Do not enable mandatory registration consent until the actual documents, version identifiers, operating entity, contact details, and applicable jurisdictions have been reviewed and approved by the product owner and qualified counsel.

## 1. Product requirements

- Registration must require affirmative acceptance of both the Terms of Service and Privacy Notice.
- Present two separate, unchecked-by-default checkboxes with accessible links to the corresponding documents.
- Do not pre-check either box. Do not bundle consent with marketing communications.
- Keep the first release free: no payment, subscription, trial, or credit-card consent.
- Registration must fail closed if either acceptance is missing, false, or refers to a stale document version.
- UI language defaults to Simplified Chinese (zh-CN); legal document language and applicable locale must be explicit. Customer reply language is unrelated.

## 2. Versioning and authoritative documents

- Maintain server-authoritative current document versions, e.g. `TERMS_VERSION` and `PRIVACY_VERSION`, in application configuration.
- The client may submit the versions it displayed, but the server must compare them to the current server values; never trust a client-selected version as authoritative.
- Store the exact immutable version accepted. Never overwrite a published document version in place.
- A material document revision must create a new version and trigger the approved re-acceptance flow before continued use where required.
- Keep drafts clearly marked DRAFT and inaccessible as active registration documents until owner approval.

## 3. Data model

Create a `legal_acceptances` table:

| Field | Type / constraint | Purpose |
|---|---|---|
| id | UUID primary key | Acceptance event identifier |
| user_id | UUID, FK users.id, NOT NULL, indexed | Account that accepted |
| document_type | enum/text: `terms` or `privacy` | Document accepted |
| document_version | text, NOT NULL | Immutable version identifier |
| accepted_at | timestamp with timezone, NOT NULL | Server-generated UTC timestamp |
| acceptance_method | text, NOT NULL, e.g. `registration_checkbox` | Capture mechanism |

Add a uniqueness constraint on `(user_id, document_type, document_version)` to avoid duplicate records for the same version. Keep the event history; do not mutate an old acceptance when a new version is accepted.

Privacy minimization: do not collect IP address, user-agent, device fingerprint, or location for consent evidence by default. Add such fields only after a documented necessity and privacy review.

## 4. Registration API behavior

- Extend the registration request with explicit booleans for Terms and Privacy acceptance and the displayed document version identifiers.
- Validate both booleans are exactly true and both versions match current server configuration.
- In one database transaction: create the pending-verification user and insert both acceptance records. If any step fails, roll back all three writes.
- Return a generic validation error for missing/stale acceptance; do not create a partially registered account.
- Existing accounts are not retroactively assigned acceptance records. Define a separate re-acceptance flow for future material revisions.
- Ensure email verification remains a separate required step before the account becomes `free_active`.

## 5. Frontend behavior

- Registration form shows two required unchecked checkboxes:
  - “我已阅读并同意《服务条款》”
  - “我已阅读并知悉《隐私声明》”
- The document links must resolve to the exact versions displayed. Do not show dead links or placeholder legal copy.
- Disable submission or show clear validation until both are checked; backend validation remains authoritative.
- On API validation failure, preserve form values where safe and clearly explain that the current document versions need to be reviewed again.
- Accessibility: labels are clickable, keyboard navigable, and screen-reader understandable.

## 6. Security and testing

Required tests:
- Reject missing Terms acceptance.
- Reject missing Privacy acceptance.
- Reject false values and stale document versions.
- Verify no user or acceptance row is committed on validation/transaction failure.
- Verify successful registration creates exactly two acceptance rows with server timestamps and current versions.
- Verify duplicate submissions do not create duplicate acceptance rows.
- Verify acceptance records are scoped to their owner and cannot be read or changed by another account.
- Verify no IP address, user-agent, or other unapproved metadata is stored.
- Verify the registration UI renders both unchecked boxes and links to the matching versions.

## 7. Product-owner / counsel decisions required before activation

- Legal operating entity name and business address.
- Support/privacy contact address and contact channel.
- Governing law, dispute forum, and intended initial user jurisdictions.
- Minimum user age and any parental-consent requirements.
- Exact service description and limitations, including AI-generated suggestions and user responsibility for review.
- Whether and how user-selected WhatsApp conversation text is sent to the configured AI processing provider; provider identity, retention, and international transfers must match the actual deployment.
- Data retention, deletion, backups, account closure, and legal-request process.
- Third-party services and subprocessors actually used (hosting, email, AI inference, analytics if any).
- Whether any optional telemetry is collected. Marketing consent must remain separate and off by default.

## 8. Release gate

This specification may be implemented in code behind an inactive configuration, but registration must not claim consent has been obtained unless the user saw and affirmatively accepted the approved, exact documents. Do not merge or deploy this work without the normal release authorization.
