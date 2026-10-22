# Roadmap

Where GuardyMed is, what is deliberately out of scope, and what comes next. The older Spanish
planning notes in this folder describe the longer-term product vision; this page is the source of
truth for what the repository does today.

## Status at v0.2.0

| Area | State |
| --- | --- |
| Scheduling: departments, people, monthly periods, shifts, overlap and date rules | Working |
| Period lifecycle: draft, in review, approved, closed, with approval decisions | Working |
| Worker self-service: own shifts, change requests with a reason, cancel | Working |
| Approving a replacement or swap moves the shift (audited) | Working |
| Attendance check-in with face verification (verified / needs review / not verified) | Working. Real model optional, simulated demo runtime by default |
| Manual fallback check-in and manager review queue | Working |
| Audit trail of every change with the acting user | Working |
| CSV exports: shifts, hours per person, attendance evidence | Working |
| Role and department scoping (manager org-wide or per department, worker own data) | Working |
| Demo data relative to today, one-command local demo, CI | Working |
| Face verification evaluation on LFW pairs | Done, see [AI_SERVICES.md](AI_SERVICES.md) |

## Out of scope today (kept honest on purpose)

- **Liveness / anti-spoofing.** A printed photo of an enrolled person would be accepted by the real model.
- **Check-in time windows.** The UI only offers check-in on the day of the shift; the API does not enforce a window or geofence.
- **Document intelligence (OCR, retrieval over scraped resolutions) and the explainable assistant.** Described in the design notes
  ([AI_ARCHITECTURE.md](AI_ARCHITECTURE.md)); no code exists yet.
- **Production deployment.** [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) is a design note. The app runs locally with SQLite;
  other databases are untested (SQLAlchemy URLs are configurable, no migrations yet).
- **Database migrations, rate limiting on sign-in, password reset, user management UI.** Accounts are seeded; roles are `manager` and `worker`.
- **Multi-template enrollment and multi-frame capture** for face verification.

## Next

1. Alembic migrations and a Postgres run in CI.
2. Check-in time window and per-shift rules enforced by the API.
3. Liveness check (blink or depth) and multi-frame capture in the real runtime.
4. Sign-in rate limiting and an admin screen for accounts.
5. Document ingestion proof of concept: OCR a resolution PDF, extract metadata, search it.

## Later

- Explainable assistant over the roster (explain conflicts, summarise changes), grounded in rule results.
- Deployment story on AWS with media in object storage and an async verification worker.

## How work is organised

`main` is stable; work happens on `feat/*` branches with Conventional Commits and semantic versions
(see [CHANGELOG.md](../CHANGELOG.md)). Tests accompany behaviour changes: `make test`.
