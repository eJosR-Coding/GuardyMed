# GuardyMed

## Overview

GuardyMed is a healthcare workforce operations MVP focused on monthly shift scheduling, worker self-service flows, approval workflows, attendance scaffolding, auditability, and operational exports.

## Problem Context

Healthcare scheduling is often managed through fragmented tools such as spreadsheets, chat messages, and manual approval flows.

That creates predictable operational problems:

- schedules are harder to validate before use
- shift changes are harder to trace
- approvals are harder to reconstruct
- exports for operations or compliance become manual work

GuardyMed is being designed to reduce that operational fragmentation with a clearer scheduling core and an auditable workflow.

For portfolio purposes, the project is framed as a system-design-heavy healthcare product rather than a startup pitch or a generic admin dashboard.

## Current Scope

The current repository scope is intentionally narrow.

It currently includes:

- a FastAPI backend scaffold
- a mounted browser MVP under `/app`
- session-based workflows for manager and worker
- scheduling, change request, approval, audit, export, and attendance scaffold endpoints
- an initial Phase A system definition and architecture direction

## Solution Direction

GuardyMed currently solves the operational core first:

- build a monthly schedule period
- assign staff to guard shifts
- enroll workers for attendance
- let workers submit manual attendance attempts
- let workers submit change requests
- let managers review queue items
- let managers review attendance attempts
- preserve audit events
- generate monthly exports

The current product story is:

- manager builds the month
- worker reacts to assigned work
- manager reviews and closes the loop

## Architecture

Current implementation is a modular monolith:

- one FastAPI app
- one mounted browser UI at `/app`
- one scheduling domain module
- one persistence path through SQLAlchemy

This keeps Phase A simple while preserving clear boundaries for later AI and CV modules.

The next planned AI boundary is face-recognition attendance only. The current MVP does not implement CV yet; it prepares the workflow and data boundaries for that future module.

## C4 Diagrams

## Deployment

Local development runs as a single FastAPI process.

- API docs: `/docs`
- mounted app: `/app`
- health check: `/health`

## Demo Accounts

- manager: `manager@guardymed.local`
- worker: `worker@guardymed.local`
- password: `password123`

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite by default for local development
- vanilla HTML, CSS, and JavaScript for the mounted MVP UI
- pytest

## Domain Model

Current core entities:

- Department
- Worker
- SchedulePeriod
- ShiftAssignment
- AttendanceEnrollment
- AttendanceAttempt
- ChangeRequest
- ApprovalDecision
- AuditEvent
- ExportJob

## API Design

Base path: `/api/v1/scheduling`

Auth model for the current MVP:

- session cookie via `/api/v1/auth/login`
- demo bootstrap via `/api/v1/auth/bootstrap-demo`
- mounted UI uses cookie-backed auth

Supported roles:

- `manager`
- `worker`

Implemented endpoints:

- `POST /auth/bootstrap-demo`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/session`
- `GET /capabilities`
- `GET /attendance/capabilities`
- `POST /demo/seed`
- `GET /departments`
- `POST /departments`
- `GET /workers`
- `POST /workers`
- `GET /attendance/enrollments`
- `POST /attendance/enrollments`
- `GET /attendance/attempts`
- `POST /attendance/attempts`
- `GET /attendance/review-queue`
- `PATCH /attendance/attempts/{attempt_id}`
- `GET /schedule-periods`
- `POST /schedule-periods`
- `GET /schedule-periods/{period_id}`
- `PATCH /schedule-periods/{period_id}`
- `GET /schedule-periods/{period_id}/calendar`
- `POST /schedule-periods/{period_id}/assignments`
- `PATCH /assignments/{assignment_id}`
- `GET /workers/{worker_id}/assignments`
- `GET /change-requests`
- `GET /change-requests/{request_id}`
- `POST /assignments/{assignment_id}/change-requests`
- `PATCH /change-requests/{request_id}`
- `GET /review-queue`
- `POST /approval-decisions`
- `GET /audit-events`
- `POST /schedule-periods/{period_id}/exports`
- `GET /schedule-periods/{period_id}/exports`
- `GET /exports/{export_id}`

Quick local run:

- `uv run uvicorn apps.api.app.main:app --reload`
- open `http://127.0.0.1:8000/app`
- load demo data from the session panel or call `POST /api/v1/auth/bootstrap-demo`

## Core Workflows

1. Manager creates a department, workers, a monthly schedule period, and assignments.
2. Manager enrolls a worker for attendance.
3. Worker views only their own assignments, then submits a change request or attendance attempt.
4. Manager reviews schedule items, worker requests, and attendance attempts.
5. Audit events and exports reflect the resulting operational state.

## Internal Docs

Useful internal references:

- architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- face-recognition attendance design: [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md)
- portfolio framing: [docs/PORTFOLIO_DIRECTION.md](docs/PORTFOLIO_DIRECTION.md)
- demo walkthrough: [docs/DEMO_FLOW.md](docs/DEMO_FLOW.md)
- portfolio research: [docs/RESEARCH.md](docs/RESEARCH.md)
- internal decisions: [docs/DECISIONS.md](docs/DECISIONS.md)

## Repository Structure

- `apps/api`: backend API and domain logic
- `apps/web`: mounted browser MVP
- `tests`: backend and route registration tests
- `docs`: product, architecture, and research notes

## Development Workflow

- `main` for stable releases
- `dev` as the integration branch
- `feature/*` branches for isolated work
- conventional commits
- semver after meaningful integration milestones

## Status

Current status:

- backend Phase A scheduling core is implemented
- session auth and role guards are implemented
- persistence is available through SQLAlchemy
- a browser MVP is available from the same FastAPI app
- manual attendance scaffold is available for enrollment, submission, and review
- test suite is green with `uv run pytest`

## Roadmap

- harden authorization and validation edges further
- add stronger export and audit filters
- replace manual attendance evidence with a CV-assisted pipeline later
- add AI/CV modules only after the scheduling core is stable
