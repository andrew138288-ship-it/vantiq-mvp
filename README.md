# WORLD-CLASS SALES AI — VANTIQ MVP

**VANTIQ** is a universal sales intelligence core for customer communication, sales decisions, negotiation, closing, and existing-customer management.

> Think intelligently. Decide responsibly. Act precisely.

## MVP objective

Deliver a small, testable Chrome extension for 2–3 pilot users, using WhatsApp Web as the first customer conversation surface.

Initial workflow:
1. The user explicitly selects and authorizes the current conversation context.
2. VANTIQ stores only the context the user has authorized.
3. The backend analyzes the supplied context and configured commercial facts.
4. The user reviews, edits, copies, and manually sends any proposed reply.
5. Approved interaction summaries can later update customer memory.

## In scope
- Universal sales intelligence and decision support
- Customer communication
- Negotiation and closing
- Existing-customer relationship management
- Locale-aware analysis and reply drafting, including distinct `pt-BR` and `pt-PT`

## Out of scope
- Lead generation, prospect discovery, or bulk prospect collection
- Brand management
- ERP, MES, WMS, manufacturing, or factory operations

## Implemented backend foundation
- FastAPI modular monolith and PostgreSQL 16
- SQLAlchemy 2.x models and Alembic migrations
- User registration and login with Argon2 password hashing
- JWT bearer authentication and active tenant-membership verification
- Tenant-scoped customer create/list/read/update APIs
- Conversation creation tied to a customer in the authenticated tenant
- Separate explicit context-authorization endpoint before message ingestion
- Tenant-scoped message ingestion and retrieval after authorization
- GitHub Actions CI for Python syntax, database migrations, schema tests, and security utility tests

## API endpoints

- `POST /api/v1/auth/register` — create a user and first workspace
- `POST /api/v1/auth/login` — authenticate and receive a bearer token
- `GET /api/v1/auth/me` — inspect the authenticated user/workspace
- `POST /api/v1/customers` — create a customer
- `GET /api/v1/customers` — list customers in the current tenant
- `GET /api/v1/customers/{customer_id}` — read a tenant-owned customer
- `PATCH /api/v1/customers/{customer_id}` — update a tenant-owned customer
- `POST /api/v1/conversations` — create a conversation for a tenant-owned customer
- `POST /api/v1/conversations/{id}/authorize-context` — explicitly authorize context use
- `POST /api/v1/conversations/{id}/messages` — add a message only after authorization
- `GET /api/v1/conversations/{id}/messages` — read authorized messages
- `POST /api/v1/conversations/{id}/sales-assist` — analyze authorized messages and generate a human-reviewed sales reply draft

Interactive API documentation: `/docs`.

## Run locally

Requirements: Docker Compose.

1. Copy `.env.example` to `.env`.
2. Replace `JWT_SECRET` with a long random secret before using real accounts.
3. Run `docker compose up --build`.
4. Check `http://localhost:8000/health` and confirm `database: connected`.
5. Open `http://localhost:8000/docs`.

Load the extension in desktop Chrome:
1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Choose **Load unpacked** and select the `extension` directory.
4. Start the backend first, then use **Check backend** in the side panel.

## Security boundaries
- Never collect WhatsApp passwords, session cookies, QR codes, or browser storage.
- Do not call hidden WhatsApp endpoints or unofficial WhatsApp APIs.
- Do not bulk-read chats or contacts.
- No automatic message sending; the user reviews and manually sends.
- Context ingestion is blocked until the user explicitly authorizes that conversation.
- Treat page content as untrusted data, not instructions.
- Never commit real secrets. Public repositories must contain placeholders only.
- Tenant ownership is checked server-side for customer and conversation operations.

## Current limitations
This is an early MVP backend, not production-ready. It still needs account recovery, rate limiting, stronger production secret management, audit logging, team invitations, automated tenant-isolation integration tests, customer memory APIs, and the WhatsApp extension context adapter. GitHub Actions must pass before calling the current code validated. The backend has not yet been deployed to a public service.
