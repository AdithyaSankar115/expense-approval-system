# Expense Approval System

A full-stack expense approval system: employees submit expenses with receipts, approvers review and act on them, with role-based permissions and an immutable audit trail.

## Stack

- **Backend:** FastAPI + SQLAlchemy + Alembic (migrations)
- **Database:** PostgreSQL (via Docker Compose)
- **Frontend:** React (Vite)
- **Auth:** JWT (24-hour expiry)

## Setup

Requires Docker, Docker Compose, and Git.

### 1. Clone the repository

```bash
git clone https://github.com/AdithyaSankar115/expense-approval-system.git
cd expense-approval-system
```

### 2. Environment variables

Copy the example file and adjust if desired (defaults work out of the box for local dev):

```bash
cp .env.example .env
```

### 3. Start Postgres

```bash
docker compose up
```

Leave this running. It starts a Postgres 16 container on port 5432, using the credentials from `.env`.

### 4. Backend setup (separate terminal)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head             # creates all 4 tables
python seed_user.py              # creates test users (see below)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs: **http://localhost:8000/docs**

### 5. Frontend setup (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

App: **http://localhost:5173**

### Test users (created by `seed_user.py`)

| Email | Password | Role | Approval limit |
|---|---|---|---|
| admin@test.com | password123 | admin | — |
| approver@test.com | password123 | approver | 500 |
| member@test.com | password123 | member | — |

## Architecture Overview

```
┌─────────────┐      HTTP/JSON       ┌──────────────┐      SQL       ┌────────────┐
│   React     │ ───────────────────► │   FastAPI    │ ─────────────► │  Postgres  │
│  (Vite)     │ ◄─────────────────── │   Backend    │ ◄───────────── │            │
└─────────────┘      JWT auth        └──────────────┘   SQLAlchemy   └────────────┘
```

Four tables: **User**, **Expense**, **ApprovalAction**, **AuditLog**. See `app/models.py` for the full schema and `alembic/versions/` for the migration that creates them.

Expense lifecycle is an explicitly-enforced state machine: `draft → submitted → approved | rejected`. Transitions are checked in code (not just accepted blindly) on every status-changing endpoint.

## Design Decisions

**AuditLog has no enforced foreign keys to User or Expense.** The assessment requires audit history to survive deletion of the referenced user or expense. A standard foreign key would either block deletion or cascade the audit rows away — both defeat the purpose. Instead, `AuditLog.user_id` and `AuditLog.expense_id` are plain UUID columns with no `ForeignKeyConstraint`, and each entry stores a denormalized JSON snapshot (`before_state`/`after_state`) of the relevant data at the time of the action. This trades strict referential integrity for guaranteed permanence — the standard tradeoff for audit logs in real systems.

**Approval limits only block approving, not rejecting.** A limit exists to prevent unauthorized *spending*, not to prevent an approver from saying no to something too large for them to authorize. The limit check only fires when `decision == "approved"`; rejection is always available to any approver/admin regardless of amount.

**Soft delete via a nullable `deleted_at` timestamp.** Deleting an expense sets this timestamp rather than removing the row. Nothing is ever truly deleted — the audit trail referencing it stays intact indefinitely, satisfying the requirement that "audit history for it remains fully intact and viewable."

**JWT expiry: 24 hours, no refresh token.** The assessment explicitly leaves refresh strategy up to the implementer. Given the scope and time available, a single 24-hour token with no refresh flow was chosen — simple, sufficient for demoing/testing, and clearly documented as a simplification rather than an oversight (see Security Notes).

**UUIDs, not auto-incrementing integers, for all primary keys.** Prevents enumeration of how many records exist or guessing adjacent IDs via the API.

**Credentials and secrets live in a git-ignored `.env` file**, never hardcoded in `docker-compose.yml`, `alembic.ini`, or source files. See Security Notes for what changes in production.

## If I Had More Time

- **Refresh tokens** and shorterlived access tokens, rather than a single 24 hour token.
- **A real "my expenses" and "all expenses" list endpoint** for members/admins (currently only the approver's pending queue is listable — members see the single expense they just created, not a full history).
- **User management endpoints.** Right now, all users (including admins) are created via `seed_user.py` directly against the database. A real system needs an admin-only `POST /users` endpoint or proper registration flow.
- **Receipt file upload.** The `receipt_path` column exists on `Expense`, but the actual file upload endpoint and local storage handling weren't built due to time.
- **Frontend polish and routing.** The current frontend is a single page with conditional rendering, no client-side routing library, and minimal styling. Functional, not polished — by design, given the time budget and that backend correctness was prioritized.
- **Automated tests.** Everything was verified manually through `/docs` and the running frontend. A real submission would include pytest coverage for the state machine, self-approval block, and approval-limit logic specifically, since those are the highest-stakes rules.
- **Pagination and filtering** on the approval queue endpoint, which currently returns every submitted expense with no limit.