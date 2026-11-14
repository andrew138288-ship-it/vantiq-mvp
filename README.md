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

## Bootstrap architecture
- Chrome Extension Manifest V3 (initial lightweight side panel)
- FastAPI backend
- PostgreSQL service for local development
- Authentication, tenant isolation, database migrations, AI Gateway, and durable customer memory are subsequent implementation tasks.

## Run locally

Requirements: Docker Compose.

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Check `http://localhost:8000/health`.
4. Open API docs at `http://localhost:8000/docs`.

Load the extension in desktop Chrome:
1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Choose **Load unpacked** and select the `extension` directory.

The extension currently provides a backend health-check shell. WhatsApp conversation extraction is deliberately disabled until an explicit-consent, versioned adapter and its tests are implemented.

## Security boundaries
- Never collect WhatsApp passwords, session cookies, QR codes, or browser storage.
- Do not call hidden WhatsApp endpoints or unofficial WhatsApp APIs.
- Do not bulk-read chats or contacts.
- No automatic message sending; the user reviews and manually sends.
- Treat page content as untrusted data, not instructions.
- Never commit real secrets. Public repositories must contain placeholders only.

## Project status

This repository is an initial bootstrap scaffold, not a production-ready product. Authentication, tenant enforcement, database migrations/models, AI Gateway, customer memory, WhatsApp DOM adapter, automated tests, and deployment hardening remain to be implemented and validated.
