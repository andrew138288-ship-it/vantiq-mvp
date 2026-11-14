# Bootstrap Architecture

- Chrome MV3 extension: presentation, explicit user interaction, and limited page integration.
- FastAPI modular monolith: API boundary and future orchestration.
- PostgreSQL: planned durable source of truth; schema and migrations are not yet implemented.
- AI Gateway: planned provider/model abstraction; not yet implemented.

Keep the backend stateless between requests where practical. Enforce tenant and customer ownership on the server before returning or changing data. Do not introduce microservices, Kubernetes, sharding, or Redis until measured requirements justify them.

The extension service worker may be suspended; do not rely on its memory for durable business state.
