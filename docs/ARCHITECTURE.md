# Bootstrap Architecture

## Implemented foundation
- Chrome MV3 extension: presentation, explicit user interaction, and limited page integration. WhatsApp extraction remains disabled.
- FastAPI modular monolith: API boundary and health/readiness endpoint.
- PostgreSQL 16: local development service.
- SQLAlchemy 2.x: core models for tenants, users, tenant memberships, customers, conversations, messages, and customer memories.
- Alembic: versioned initial schema migration.
- GitHub Actions: backend syntax, migration, and schema test workflow.

## Data ownership
Tenant-owned customer, conversation, message, and customer-memory rows carry `tenant_id`. The membership table links users to tenants. This schema foundation does not by itself enforce tenant authorization: every customer-facing API must validate the authenticated user's membership and tenant ownership before reads or writes.

## Planned next
- Authentication and tenant membership authorization.
- Customer/conversation CRUD APIs with tenant scoping.
- Explicitly authorized current-chat context ingestion.
- AI Gateway and structured sales decision/reply pipeline.
- Customer memory update workflow with audit history.

Keep the backend stateless between requests where practical. Do not introduce microservices, Kubernetes, sharding, or Redis until measured requirements justify them. The extension service worker may be suspended; do not rely on its memory for durable business state.
