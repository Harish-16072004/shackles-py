# Shackles Symposium (`shackles-py`)

Async Python 3.12+ / FastAPI backend for the **Shackles National-Level Technical Symposium** platform. Manages participant registration, payment verification, atomic Shackles ID allocation (`SH{YY}{TYPE}{NNN}`), QR ticket generation, printable A3 PDF ID cards, team & invitation workflows, two-phase paper submissions, multi-judge weighted rubrics & leaderboards, and offline-capable station QR scanning.

## Architecture & Tech Stack

- **Web Framework**: FastAPI + Uvicorn (async HTTP, OpenAPI docs at `/docs`, structured `DomainError` exception envelopes)
- **Database & ORM**: PostgreSQL 15 + SQLAlchemy 2.1 (`asyncpg`) + Alembic migrations (Prisma-compatible camelCase column mappings)
- **Cache, Rate Limiting & Job Queue**: Valkey 8 / Redis + `slowapi` rate limiting + `arq` background workers
- **Authentication**: JWT (`HS256` via `python-jose`) + `bcrypt` (12 rounds) + role & fine-grained permission guards (`RolePermission`)
- **Ticketing & Print Generation**: `qrcode`, `Pillow`, and `ReportLab` (300 PPI card compositing arranged 4×4 on A3 PDF sheets)
- **Transactional Emails**: In-memory `Jinja2` HTML templates dispatched via ARQ workers to **Resend HTTP API**, **SMTP / MailHog**, or console stdout fallback

## Project Structure

```text
src/shackles/
├── main.py                  # FastAPI lifespan, middleware, static mounts, router registration
├── config.py                # Pydantic Settings (.env loader)
├── errors.py                # DomainError hierarchy and stable error codes
├── db/                      # AsyncEngine, async_sessionmaker, DeclarativeBase
├── models/                  # 16 SQLAlchemy ORM models + 16 domain Enums
├── schemas/                 # 15 Pydantic v2 input/output schema modules
├── repositories/            # 19 repository classes encapsulating SQL queries & optimistic locking
├── services/                # 9 domain services + QR, A3 PDF ID cards, tokens, and email templates
├── workers/                 # ARQ worker settings, Redis pool helpers, and background jobs
└── api/
    ├── deps.py              # JWT auth, role guards (Admin/Staff), and fine-grained permission guards
    ├── errors.py            # DomainError -> HTTP status translation
    └── routes/              # Public, participant, staff scanner, and admin sub-routers
```

## Quick Start (Local Development)

### 1. Start Infrastructure (Postgres, Valkey, pgAdmin, MailHog)

```bash
cp .env.example .env
docker compose up -d
```

- **PostgreSQL 15**: `localhost:5432` (`shackles` / `shackles_dev`)
- **Valkey 8 (Redis)**: `localhost:6379`
- **pgAdmin 4**: `http://localhost:5050`
- **MailHog Web UI**: `http://localhost:8025` (SMTP on `localhost:1025`)

### 2. Install Dependencies & Run Migrations

```bash
uv sync
uv run alembic upgrade head
```

### 3. Run the API Server & Background Worker

```bash
# Terminal 1 — FastAPI web server
uv run uvicorn shackles.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — ARQ background worker (QR generation, emails, CSV exports, invite cleanup)
uv run arq shackles.workers.settings.WorkerSettings
```

### 4. Run Tests, Linting & Type Checking

```bash
# Unit & API test suite
uv run pytest

# End-to-end database lifecycle script (requires running Postgres)
uv run python integration_test.py

# Lint & typecheck
uv run ruff check src tests
uv run mypy src
```

## API Overview

| Prefix | Access | Description |
| :--- | :--- | :--- |
| `/api/health` | Public | Database connectivity and active year readiness probe |
| `/api/auth` | Public | Register (`/register`), login (`/login`), forgot/reset password |
| `/api/users/me` | Authenticated | Profile read (including QR token/URL), profile update, password change |
| `/api/events` | Public | Active symposium events & workshops listing and detail lookup |
| `/api/payments` | Authenticated | Proof image upload (`/upload-proof`), payment submission (`POST /`), status (`GET /me`) |
| `/api/events/{id}/register` | Authenticated | Individual event registration with package, capacity, and time-clash checks |
| `/api/registrations/me` | Authenticated | Current user's event registrations for the active year |
| `/api/teams` | Authenticated | Create team, join by code or invite token, list my teams (`/me`), send invites, lock team, remove member |
| `/api/teams/{id}/paper` | Team / Staff | View paper submission status, upload abstract (`/abstract`), upload presentation (`/presentation`) |
| `/api/accommodation` | Authenticated | Request (`POST /`), view (`GET /me`), or cancel (`DELETE /me`) accommodation |
| `/api/contact` | Public / Optional Auth | Submit contact form inquiry |
| `/api/scanner` | Staff | Decode QR (`/decode`), mark attendance (`/attendance`), issue kit (`/kit`), scan history, on-spot kiosk profile |
| `/api/admin/*` | Admin | Dashboard stats, users & roles, event CRUD, payment verification & QR regen, teams & bulk on-spot registration, judging rubrics & leaderboards, paper selection & deadlines, staff assignments, role permissions, accommodations, contact messages, CSV exports, and A3 ID card PDF generation |
