# Deployment preparation — no publication performed

This delivery stays local at the user's request. The container configuration is a preparation artifact; Docker is not installed on the development machine, so container builds and a public host have not been verified.

## Container stack

Install Docker on the target machine. Configure a deployment-specific `.env` with a strong random `POSTGRES_PASSWORD`, a different strong random `JWT_SECRET`, `DEMO_MODE=false`, explicit HTTPS `CORS_ORIGINS`, and optional `OPENAI_API_KEY`/`OPENAI_MODEL`. Do not copy the local `.env` or demo database.

```sh
docker compose build
docker compose up -d
```

The frontend listens on loopback port 8080, nginx forwards `/api/` to FastAPI, and PostgreSQL stays on the private compose network. Put a TLS reverse proxy in front of port 8080 on the target host. The backend loopback port 8000 is exposed for local operator access only. Database and image files use durable named volumes.

## Create the first production administrator

With demo mode disabled the application must not seed public demo accounts. Create the first administrator using the interactive helper in `backend/app/create_admin.py` inside the private container. Supply the initial password through secure input, never a command-line argument or committed file. Then manage users through the authenticated administration interface.

```sh
docker compose exec backend python -m app.create_admin
```

The helper prompts for the password without echo and rejects an existing email. Configure a private managed PostgreSQL URL and durable upload volume if deploying backend and frontend separately. Preserve `/api` same-origin routing or explicitly configure allowed origins.

## Before exposure

Run the backend and browser acceptance suite in a staging environment, verify HTTPS and restricted origins, confirm demo shortcuts are disabled, test user/role isolation, set retention rules, test PostgreSQL and upload backups, and configure monitoring and provider budgets. Supply authentic zone geometry/history before claiming operational coverage. The heuristic model requires independent evaluation before real civic decision use.

## Data migration

The initial schema is in `database/001_schema.sql`. Application startup also creates missing initial tables. Later production schema changes require versioned SQL migrations and a backup; `create_all` is not a production migration system. Never reset a production database with the synthetic seed script.
