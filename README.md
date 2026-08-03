# GuardyMed

## Overview

GuardyMed is a healthcare operations platform focused on monthly shift scheduling, approval workflows, auditability, and operational exports.

## Problem Context

Healthcare scheduling is often managed through fragmented tools such as spreadsheets, chat messages, and manual approval flows.

That creates predictable operational problems:

- schedules are harder to validate before use
- shift changes are harder to trace
- approvals are harder to reconstruct
- exports for operations or compliance become manual work

GuardyMed is being designed to reduce that operational fragmentation with a clearer scheduling core and an auditable workflow.

## Current Scope

The current repository scope is intentionally narrow.

It currently includes:

- a FastAPI backend scaffold
- a mounted browser MVP under `/app`
- role-based scheduling workflows for coordinator, worker, and approver
- scheduling, change request, approval, audit, and export endpoints
- an initial Phase A system definition and architecture direction

## Solution Direction

GuardyMed currently solves the operational core first:

- build a monthly schedule period
- assign staff to guard shifts
- let workers submit change requests
- let approvers review queue items
- preserve audit events
- generate monthly exports

## Architecture

Current implementation is a modular monolith:

- one FastAPI app
- one mounted browser UI at `/app`
- one scheduling domain module
- one persistence path through SQLAlchemy

This keeps Phase A simple while preserving clear boundaries for later AI and CV modules.

## C4 Diagrams

## Deployment

Local development runs as a single FastAPI process.

- API docs: `/docs`
- mounted app: `/app`
- health check: `/health`

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
- ChangeRequest
- ApprovalDecision
- AuditEvent
- ExportJob

## API Design

Base path: `/api/v1/scheduling`

Auth model for the current MVP:

- `x-user-id`
- `x-user-role`

Supported roles:

- `coordinator`
- `worker`
- `approver`

Implemented endpoints:

- `GET /capabilities`
- `POST /demo/seed`
- `GET /departments`
- `POST /departments`
- `GET /workers`
- `POST /workers`
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
- load demo data from the session panel or call `POST /api/v1/scheduling/demo/seed`

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
- auth headers and role guards are implemented
- persistence is available through SQLAlchemy
- a browser MVP is available from the same FastAPI app
- test suite is green with `uv run pytest`

## Roadmap

- merge current Phase A browser MVP into `dev`
- replace header-based demo auth with a real session/auth flow
- add ownership checks for worker-scoped data
- add stronger export and audit filters
- add AI/CV modules only after the scheduling core is stable
