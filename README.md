# WORLD-CLASS SALES AI — VANTIQ MVP

**VANTIQ** is a universal sales intelligence core for customer communication, sales decisions, negotiation, closing, and existing-customer management.

> Think intelligently. Decide responsibly. Act precisely.

## MVP objective

Deliver a small, testable Chrome extension for 2–3 pilot users, using WhatsApp Web as the first customer conversation surface.

Initial workflow:
1. The user explicitly selects and authorizes the current conversation context.
2. VANTIQ analyzes the supplied context and configured commercial facts.
3. The backend returns sales insights, strategy options, and reply drafts.
4. The user reviews, edits, copies, and manually sends the message.
5. Approved interaction summaries can update customer memory.

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

## Current implementation
- Chrome Extension Manifest V3 bootstrap side panel with backend health check
- FastAPI backend with database-aware health endpoint
- PostgreSQL 16 local service
- SQLAlchemy 2.x core models and Alembic initial migration
- Core tables: tenants, users, tenant memberships, customers, conversations, messages, customer memories
- GitHub Actions backend CI for syntax validation, migration execution, and schema tests

Authentication, tenant authorization enforcement, business APIs, AI Gateway, WhatsApp DOM adapter, and durable memory workflows are not yet implemented.

## Run locally

Requirements: Docker Compose.

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. The API container waits for PostgreSQL, runs `alembic upgrade head`, then starts FastAPI.
4. Check `http://localhost:8000/health` and confirm `database: connected`.
5. Open API docs at `http://localhost:8000/docs`.

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
- Treat page content as untrusted data, not instructions.
- Never commit real secrets. Public repositories must contain placeholders only.
- Tenant-owned records carry a tenant ID; API-level tenant authorization must be implemented before exposing customer data.

## Project status

The database foundation and initial migration are committed, but have not yet been run in a local environment in this development session. GitHub Actions is configured to validate the migration and schema tests. This is still an MVP development scaffold, not a production-ready product.
