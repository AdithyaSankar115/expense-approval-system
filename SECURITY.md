# Security Notes

## What's secured

- **Passwords are hashed with bcrypt** (via `passlib`), never stored or logged in plaintext, and never reversibly encrypted. `hash_password`/`verify_password` in `app/auth.py`.

- **JWT-based authentication**, tokens signed with a secret key (`JWT_SECRET_KEY`), 24-hour expiry, verified on every protected endpoint via a shared `get_current_user` dependency.

- **Self-approval is blocked unconditionally**, regardless of role  checked server-side in `approve_or_reject_expense`, not just hidden in the frontend UI.

- **Approval limits are enforced server-side**, returning a `403` if an approver attempts to approve (not reject) an expense above their limit. Admins bypass this by design, matching the "full access" requirement.

- **Role-based access control is checked on the backend for every state-changing endpoint**  the frontend hides UI elements a role shouldn't see, but this is a UX convenience, not the actual enforcement boundary.

- **Secrets (database credentials, JWT signing key) live in a git-ignored `.env` file**, never hardcoded into `docker-compose.yml`, `alembic.ini`, or any committed source file. `.env.example` documents the expected variable names without real values.

- **CORS (Cross Origin Resource Sharing) is explicitly restricted** to `http://localhost:5173` (the frontend's dev origin) rather than left wide open.

- **Immutable audit logging**: on every create/submit/approve/reject/delete action, with no foreign key allowing the log entries to be deleted alongside the user or expense they reference.

- **Soft delete**: expenses are never physically removed from the database, preserving audit history indefinitely.

## What was knowingly left out (given the time-boxed scope)

- **No refresh token flow.** A single 24-hour access token is used; there's no way to renew a session without logging in again, and no way to revoke a token before it expires short of rotating the signing key (which would invalidate every active session, not just one).

- **No rate limiting** on `/login` or any other endpoint  a real deployment would need this to prevent brute-force credential guessing.

- **No password complexity requirements** on the (currently script-only) user creation path.

- **No HTTPS/TLS**: everything runs over plain HTTP locally, which is appropriate for local development only.

- **No file upload validation or size limits**: receipt upload wasn't implemented in this timeframe, but even the `receipt_path` field as designed doesn't yet include a plan for validating file type or size.

- **No input sanitization beyond Pydantic's type validation**: amounts, categories, etc. are type-checked but not bounded (e.g., nothing stops a negative amount or an absurdly large one).

- **No account lockout after repeated failed logins.**

- **The JWT secret key is a plain string in `.env`**, not a securely generated random value, and not rotated.

## What a production deployment would need

- **A managed database service** (e.g. AWS RDS, Google Cloud SQL) instead of a local Docker container, with automated backups, TLS-enforced connections, and network-level access restriction (only the backend can reach it, not the open internet).

- **A real secrets manager** (AWS Secrets Manager, HashiCorp Vault, or the hosting platform's environment variable configuration) rather than a `.env` file the application code reading `os.environ[...]` wouldn't need to change, only how those variables get injected.

- **HTTPS enforced everywhere**, with the JWT and all credentials only ever transmitted over TLS.

- **Refresh tokens with shorter-lived access tokens**, plus a way to revoke sessions (e.g. a token denylist or short-lived tokens checked against a "last password change" timestamp).

- **Rate limiting and account lockout** on authentication endpoints.

- **Structured logging and monitoring** separate from the audit trail (the audit trail is a business record, not an operational/security log).

- **Regular dependency scanning**: this project pins `bcrypt==4.0.1` for compatibility reasons found during development; a production system would need a process for tracking and updating pinned versions safely.