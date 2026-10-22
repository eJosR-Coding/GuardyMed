# Changelog

All notable changes to GuardyMed. Versions follow [Semantic Versioning](https://semver.org/).

## 0.2.0

First version that is meant to be used and judged end to end.

### Added
- Redesigned web app: a calm, minimal interface with a small set of screens per role
  (manager: Today, Schedule, Attendance, Team, Activity; worker: My shifts, My requests).
- Face verification outcomes the product can explain: verified, needs review, not verified.
- `GET /attendance/cv/status` reports the active runtime, thresholds and any fallback reason.
- Evaluation script and results for face verification on the public LFW test pairs.
- Approving a replacement or swap request now moves the shift to the replacement worker (audited).
- Exports contain real CSV tables: shifts, hours per person, attendance evidence.
- Demo data relative to today's date: five workers, an approved previous month, a draft current month.
- Consistent API error envelope (`detail` + `code`, and `fields` for validation errors).
- Makefile (`make demo`, `make test`, `make build`), GitHub Actions CI, and an English roadmap.

### Changed
- Department scoping is enforced for managers and workers (the guard used to be a no-op).
- Passwords use a random per-user salt; approval decisions are attributed to the signed-in user.
- Default face thresholds are calibrated for the InsightFace `buffalo_l` model (see `docs/AI_SERVICES.md`).
- Tests run against a throwaway database instead of the developer's `guardymed.db`.
- Frontend no longer depends on PrimeVue; fonts are self-hosted.

### Fixed
- Real face runtime crashed on `normed_embedding` (ambiguous array truth value).
- A capture without a usable face left an orphan enrollment or a pending attendance attempt.
- Comparing a template from another model crashed instead of returning a clear error.

## 0.1.1

- Stabilised manager and worker demo flows, fixed `/app` asset paths, added C4 diagrams.
