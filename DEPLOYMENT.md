# VANTIQ backend deployment preparation

## Target platform

Railway managed application hosting and managed PostgreSQL, initially in Singapore
(`asia-southeast1-eqsg3a`). Keep the API and database in the same region.

This is a deployment runbook. No Railway project, database, public endpoint, or
production secret has been created by this repository change.

## Railway project setup

1. Sign in to Railway and create a project from the GitHub repository
   `andrew138288-ship-it/vantiq-mvp`, branch `main`.
2. Create a PostgreSQL service in the same Railway project.
3. Set the PostgreSQL service and API service region to Singapore.
4. For the API service, set the root directory to `/backend`; Railway will
   build using `backend/Dockerfile`.
5. Add a reference variable to the API service:
   `DATABASE_URL=${{Postgres.DATABASE_URL}}` (select the actual PostgreSQL
   service name in Railway's variable picker).
6. Set these API service variables:
   - `APP_ENV=production`
   - `APP_NAME=VANTIQ API`
   - `JWT_SECRET` = a newly generated random secret of at least 32 bytes
   - `ACCESS_TOKEN_MINUTES=60`
   - `OPENAI_API_KEY` = add only after the API service and database are ready
   - `OPENAI_MODEL=gpt-6-astra`
7. Set the pre-deploy command to `alembic upgrade head`.
8. Set the start command to
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
9. Set the healthcheck path to `/health` and timeout to at least 120 seconds.
10. Generate a Railway public domain only when ready to run the smoke test.

## Deployment verification

- Build completes from the backend root directory.
- Pre-deploy migration exits successfully.
- Service becomes healthy at `/health`.
- Health response reports `database: connected`.
- `GET /api/v1` returns the VANTIQ API identity.
- Register/login/customer/conversation authorization flows are tested.
- AI is tested only after adding the secret in Railway's secret variable UI.
- Never commit `.env`, database credentials, JWT secrets, or provider API keys.

## Cost and data safeguards

- Review Railway usage limits and estimated usage before enabling paid resources.
- Keep the API and database in Singapore and on the private network.
- Enable and verify database backups before storing pilot customer data.
- Use synthetic test data until access controls, backups, and production checks
  have been independently verified.
