# AI Usage Log

This project was built with Claude acting as a mentor and pair-programmer, not a silent code generator. Claude was explicitly instructed to explain concepts before writing code and to walk through tradeoffs on design decisions rather than just producing a finished system. Below is a representative log of prompts used, organized by phase, along with where output was corrected, rejected, or overridden.

## Environment & infrastructure setup

**Prompt:** *"Explain how a senior developer mentally breaks down a full-stack system from scratch, then give me a toolkit list and a step-by-step roadmap for this expense approval assessment. Don't write functional code yet."*
→ Used to establish an overall build order (data layer → business logic → API → auth → frontend) before touching any code, and to get an accurate list of local tools to install (Docker Desktop, Python, Node via nvm, VS Code, Git).

**Prompt:** *"My WSL install is stuck at 0%, and Docker gives me a 'virtualization support not detected' error."*
→ Used repeatedly during a genuinely difficult setup stretch (BIOS virtualization, a subsequent WSL hang at 59%, then a disk-space failure caused by a nearly-full C: drive). Each fix was tested and confirmed before moving to the next step rather than applying a batch of unverified changes.

**Prompt:** *"Explain what Docker and WSL2 are."*
→ Used to build genuine understanding of the environment before relying on it, rather than treating Docker commands as magic incantations to copy-paste.

## Database design

**Prompt:** *"AuditLog needs to survive deletion of the user or expense it references. Explain the tradeoff between a nullable foreign key and no foreign key at all before we pick one."*
→ Claude presented both options with real tradeoffs rather than picking one silently. The no-FK-plus-denormalized-snapshot approach was chosen after understanding *why*, and is documented as a Design Decision in the README rather than applied as an unexplained default.

**Prompt:** *"Give me the complete SQLAlchemy models for User, Expense, ApprovalAction, and AuditLog based on what we just designed."*
→ Generated the initial `app/models.py`. Reviewed line by line before running the Alembic migration, confirmed the UUID primary keys, the enum-based `role`/`status` fields, and specifically the absence of a `ForeignKeyConstraint` on `AuditLog.user_id`/`expense_id` matched the design decision above.

## Backend business logic

**Prompt:** *"Write the approval endpoint: only approvers/admins can act, expense must be 'submitted', self-approval is blocked regardless of role, and approvers can't approve above their limit. Admins bypass the limit."*
→ This produced the core `approve_or_reject_expense` logic. Verified correctness by deliberately trying to break each rule (approving your own expense as admin, approving over-limit as a capped approver) rather than trusting the code because it looked right.

**Prompt:** *"When I try to reject an expense that's over my approval limit, I can't, is that intended?"*
→ This was a real bug I noticed during manual testing, not something Claude flagged proactively. Claude's first implementation checked the limit before checking the decision type, blocking rejection as well as approval. After discussing it, we agreed a limit should only restrict *authorizing spend*, not *declining* it  the fix moved the limit check to only apply when `decision == "approved"`.

## Debugging (real errors encountered)

**Prompt (pasted a full traceback):** *`fastapi.exceptions.ResponseValidationError: ... 'Input should be a valid dictionary or object to extract fields from', 'input': None`*
→ Diagnosed as `db.get()` returning `None` intermittently right after `db.commit()`. Fixed by using `db.refresh(expense)` on the already-in-memory object instead of re-querying  Claude explained why the original pattern was unreliable rather than just supplying a fix to paste.

**Prompt (pasted a traceback):** *`AttributeError: module 'bcrypt' has no attribute '__about__'`*
→ Identified as a version incompatibility between a newer `bcrypt` release and `passlib`. Resolved by pinning `bcrypt==4.0.1`, a specific known fix rather than a guess.

**Prompt:** *"Give me the whole file, not fragments to merge myself it's causing sync issues."*
→ After several rounds of partial edits causing files to drift out of sync with what Claude intended (e.g. a missing `submit_expense` endpoint after a partial patch), the workflow was explicitly changed to always request complete file contents rather than incremental diffs, specifically to reduce copy-paste error risk under time pressure.

## Frontend

**Prompt:** *"Build a login screen and a dashboard: expense creation for everyone, an approval queue only visible to approvers/admins pull role from the JWT."*
→ Generated the initial `App.jsx`. Verified the role based visibility requirement specifically by logging in as each of the three seeded roles and confirming a `member` never sees the approval queue at all (not just disabled).

**Prompt:** *"Approving/rejecting through the UI does nothing when a rule blocks it — no error shows."*
→ A real usability gap: the original `handleApprove` silently swallowed FastAPI's error responses. Fixed by checking for a `detail` field in the response and surfacing it via an alert, so a blocked action (e.g. self-approval) is now visibly explained rather than looking identical to a bug.

## Documentation

**Prompt:** *"Draft the README, PROMPTS.md, and Security Notes based on everything we actually built and decided, not a generic template."*
→ Used to produce first drafts of all three documents, grounded in this session's actual decisions and bugs rather than boilerplate. Reviewed and edited afterward this file itself was revised to include specific representative prompts rather than only summarized outcomes, per direct feedback that the first draft read as too generic.

## Overall judgment exercised

- Chose to prioritize backend correctness and audit logging over frontend polish once time became constrained, based on the assessment's explicit evaluation criteria rather than defaulting to "build everything a little."
- Rejected Claude's first explanation of the approval-limit hardcoded-password question ("is this a security flaw") as too simplistic, pushed back, and arrived at a more precise answer distinguishing exploitation risk from process/perception risk.
- Caught and corrected a syntax error in Claude-generated code (`CryptContext(schemes=["bcrypt", deprecated="auto"])` — a misplaced closing bracket) by reading the Python traceback rather than assuming generated code was correct by default.