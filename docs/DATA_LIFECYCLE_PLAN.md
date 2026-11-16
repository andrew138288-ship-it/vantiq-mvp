# VANTIQ Data Lifecycle Plan

**Status:** Engineering plan; not a legal notice or a promise of complete erasure.

## Current implementation

- The authenticated customer deletion endpoint is tenant-scoped. It explicitly deletes the customer's messages, conversations, customer-memory row, and customer row in one database transaction.
- The authenticated conversation deletion endpoint is tenant-scoped. It explicitly deletes the conversation's messages and conversation row in one database transaction.
- Both operations return not-found for records outside the active tenant.
- The analysis-context message cap is enforced server-side at 20 messages per conversation.
- Password reset revokes active refresh sessions and invalidates prior access tokens through the user's token version.

## Not yet implemented or verified

- Account closure and deletion of all account/workspace data.
- User-facing data export.
- A product-wide retention period or scheduled expiry/deletion job.
- Deletion from database backups, infrastructure logs, email-provider systems, or AI-provider systems.
- A verified inventory of all subprocessors, provider retention settings, processing locations, and deletion APIs.
- A user-facing deletion confirmation and completion receipt.

## Safe implementation sequence

1. Keep customer and conversation deletion tenant-scoped and covered by automated tests.
2. Implement account closure only after defining behavior for accounts with multiple workspace memberships. The safe default is to block closure if another member would be left without an owner, rather than silently deleting shared workspace data.
3. Add an export workflow before account closure is exposed in the UI, so users can retrieve their records.
4. Choose retention periods only after the actual product data flow, operational needs, applicable legal requirements, and provider retention controls have been reviewed. Do not silently invent a duration in code.
5. Add scheduled expiry and operational deletion only after the retention policy is approved.
6. Document backup expiry and third-party deletion limits only after they have been verified with the actual infrastructure and providers.

## Important limitation

The current customer and conversation deletion endpoints delete rows from the application's primary database transaction. They do not establish that copies in backups, infrastructure logs, outbound email systems, or third-party AI systems are also erased. Do not describe this as complete or immediate erasure across all systems.
