# VANTIQ account session management specification

Status: implementation is present on the `feat/react-whatsapp-dock` branch. CI and real end-to-end validation are still required before this can be considered complete or production-ready.

## Goals

- Keep the first release free; session security must not depend on a paid plan.
- Support secure access-token renewal without asking the user to sign in every hour.
- Let a user inspect active sessions, revoke one session, or revoke every session.
- Keep refresh credentials out of WhatsApp page storage and ordinary application logs.
- Password reset and account suspension must revoke all active sessions.

## Token model

- Access token: short-lived JWT (target 15 minutes), signed with the configured server secret. Claims include subject, tenant, role, token version, issued-at and expiry.
- Refresh token: cryptographically random opaque value (at least 256 bits of entropy). Store only its SHA-256 digest server-side.
- Refresh token lifetime: 30 days, with rotation on every successful refresh.
- Rotation is single-use: atomically revoke/consume the presented refresh token and create a replacement. Reuse of a consumed token revokes the entire token family/session chain and requires a fresh login.
- A refresh token is bound to one server-side session record. Store created/last-used/expiry/revoked timestamps, a non-authoritative user-agent label, and a coarse IP value only if operationally required. Never store raw refresh tokens.
- No refresh token is exposed in URLs, query strings, analytics, error messages, or logs.

## Required API

- POST /api/v1/auth/refresh: accept the refresh token in the request body; atomically rotate it and return a new access token and refresh token.
- POST /api/v1/auth/logout: revoke the presented refresh session. Idempotent response.
- POST /api/v1/auth/logout-all: revoke every refresh session for the authenticated user and increment token_version, invalidating outstanding access tokens.
- GET /api/v1/auth/sessions: return the authenticated user's active sessions, newest first. Return session ID, created time, last-used time, expiry, and a safe device label; never return token hashes.
- DELETE /api/v1/auth/sessions/{session_id}: revoke only a session owned by the authenticated user. Return not-found for sessions outside the user's account.
- Password-reset completion, account suspension, and account closure revoke every refresh session and increment token_version.

## Client requirements

- Store refresh credentials only in chrome.storage.session for the first extension release; never in page localStorage, DOM, or WhatsApp storage.
- Refresh automatically once when an API request receives 401, then retry that request at most once.
- If refresh fails, clear the extension session and request sign-in. Never loop retries.
- Explicit logout calls the server revocation endpoint before clearing local session state; clear local state even if the network is unavailable.
- Add account UI for active sessions and revoke-one/revoke-all actions. Do not expose raw tokens.
- No automatic logout based only on elapsed UI time while the server session remains valid.

## Required tests

- Successful login creates one refresh session; only the token digest is persisted.
- Successful refresh rotates the token and invalidates the previous token.
- Concurrent or repeated use of a refresh token cannot create multiple valid descendants.
- Expired, revoked, malformed, or unknown refresh tokens are rejected.
- Reuse detection revokes the session chain.
- Logout revokes one session; logout-all revokes all sessions and invalidates access tokens.
- A user cannot list or revoke another user's sessions.
- Password reset invalidates all refresh sessions.
- Session responses never contain refresh token material.

## Rollout constraints

- Add a forward-only Alembic migration; do not rewrite existing migrations.
- Preserve existing verified free accounts.
- Keep the API backwards compatible during the extension transition where practical.
- Do not deploy until migration, backend tests, extension tests, and a real end-to-end refresh/logout smoke test pass.
