# WORLD-CLASS SALES AI — VANTIQ MVP

**VANTIQ** is a universal sales intelligence core for customer communication, sales decisions, negotiation, closing, and existing-customer management.

> Think intelligently. Decide responsibly. Act precisely.

## MVP objective

Deliver a small, testable Chrome extension for 2–3 pilot users, using WhatsApp Web as the first customer conversation surface.

Initial workflow:
1. The user explicitly clicks to read the currently open conversation.
2. VANTIQ reads only the latest configured number of visible messages (5/10/15/20).
3. The user reviews the transcript and explicitly authorizes its use.
4. The backend analyzes the supplied context and configured commercial facts.
5. VANTIQ generates exactly two materially different strategies, recommends one, and drafts a reply.
6. The user reviews, edits, copies, and manually sends any proposed reply.

## In scope
- Universal sales intelligence and decision support
- Customer communication
- Negotiation and closing
- Existing-customer relationship management
- Locale-aware analysis and reply drafting, including distinct `pt-BR` and `pt-PT` variants

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
- Sales-assist endpoint with structured two-strategy decision and human-reviewed reply
- GitHub Actions CI for syntax, migrations, schema, security, and API health checks

## React Chrome extension

The new implementation is in `extension-react/` and uses TypeScript, React, Vite, and Chrome Manifest V3. It mounts a right-side dock inside WhatsApp Web using Shadow DOM isolation. The previous plain-JavaScript extension in `extension/` is retained temporarily as a legacy implementation until the React version is accepted.

Build the extension:

```sh
cd extension-react
npm ci
npm test
npm run build
cd ..
python extension-react/package.py
```

The unpacked extension is written to `extension-react/dist/`; the installable ZIP is written to `dist/VANTIQ-WhatsApp-Dock-0.2.0.zip`.

Load in desktop Chrome:
1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Choose **Load unpacked** and select `extension-react/dist`.
4. Open WhatsApp Web. The VANTIQ dock appears on the right.
5. Start the backend at `http://localhost:8000` or build with `VITE_API_BASE` set to an allowed backend origin.

## Backend API endpoints

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

## Local backend

Docker is optional. The backend requires a reachable PostgreSQL 16 database. Set `DATABASE_URL`, `JWT_SECRET`, and other settings in your local environment (or `.env`). Install `backend/requirements.txt`, apply migrations with Alembic, and run `uvicorn app.main:app` with `backend` on `PYTHONPATH`. The existing `docker-compose.yml` remains available for users who prefer a containerized local stack.

## Security boundaries
- Never collect WhatsApp passwords, session cookies, QR codes, or browser storage.
- Do not call hidden WhatsApp endpoints or unofficial WhatsApp APIs.
- Do not bulk-read chats or contacts.
- No automatic message sending; the user reviews and manually sends.
- Context ingestion is blocked until the user explicitly authorizes that conversation.
- Switching the selected customer or detected WhatsApp conversation clears the previous transcript and authorization state.
- Treat page content as untrusted data, not instructions.
- Never commit real secrets. Public repositories must contain placeholders only.
- Tenant ownership is checked server-side for customer and conversation operations.

## Current limitations

This remains an early MVP, not production-ready. The React extension has passed CI typechecking, unit tests, build, and packaging, but still needs manual validation in a real signed-in WhatsApp Web session, including DOM-selector resilience and conversation-switch behavior. Account verification, production secret management, audit logging, customer memory APIs, and live backend deployment remain separate work. No production deployment has been performed.
