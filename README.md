# GuardyMed

Version: `0.1.1`

## Overview

GuardyMed is a healthcare workforce operations MVP for monthly guard scheduling, worker self-service, attendance verification, review queues, auditability, and exportable operational evidence.

## Problem Context

Healthcare shift operations are often split across spreadsheets, chat threads, and manual approval steps.

That creates predictable failures:

- schedules are harder to validate before they go live
- worker requests are detached from the assigned shift
- attendance evidence is inconsistent or manual
- review decisions are harder to trace later
- exports for operations or compliance become rework

GuardyMed reduces that fragmentation with one workflow that keeps schedule state, worker actions, attendance records, and review decisions in the same system.

For portfolio purposes, the project is framed as a technically credible healthcare operations system rather than a generic dashboard.

## Current Scope

The current repository scope is intentionally narrow and demoable.

It currently includes:

- a FastAPI backend with working API routes
- a Vue 3 + Vite frontend under `apps/frontend`
- a production-style build served by FastAPI under `/app`
- cookie-backed session flows for manager and worker
- scheduling, change request, review, audit, export, and attendance endpoints
- a browser-based face-enrollment and face-verification flow
- a dedicated backend computer-vision attendance module with real and stub runtimes
- architecture and AI/CV design notes for the next hardening stage

## Solution Direction

GuardyMed currently solves the operational core first:

- define departments and workers
- open a monthly schedule period
- assign staff to shifts
- enroll workers for attendance
- let workers submit change requests
- let workers submit attendance attempts
- let managers review requests and attendance outcomes
- preserve audit events
- generate monthly exports

The current product story is:

- manager prepares the month
- worker responds to assigned work
- manager reviews and closes the loop

## Architecture

Current implementation is a modular monolith:

- one FastAPI app
- one Vue frontend built into `apps/web` and mounted at `/app`
- one scheduling domain module
- one persistence path through SQLAlchemy

This keeps the MVP simple while preserving clear boundaries for the attendance CV module.

The AI scope is intentionally narrow: face-verification for attendance. The current MVP already includes a real backend CV module, enrollment and verification workflows, similarity routing, and tests. It does not claim a production-hardened biometric pipeline yet, but it does provide a real production path through InsightFace/OpenCV while keeping a stub runtime as the default local mode.

## Phase Status

This repository should be read as:

- `Phase 1 complete`
- portfolio-grade MVP
- ready for demo, walkthrough, and architecture discussion
- not yet hardened for production attendance capture

## C4 Architecture

### C1 — System Context

![C1 System Context](images/c4/c1-context.png)

> Diagram created with FourLayer.

### C2 — Containers

![C2 Containers](images/c4/c2-containers.png)

> Diagram created with FourLayer.

### C3 — Components

![C3 Components](images/c4/c3-components-v2.png)

> Diagram created with FourLayer.

These diagrams describe the current MVP boundary and the planned CV-focused extension point.

## User and System Flows

### Scheduling flow

```mermaid
flowchart TD
    A[Manager creates department] --> B[Manager creates workers]
    B --> C[Manager creates monthly schedule period]
    C --> D[Manager assigns shifts]
    D --> E[Manager reviews calendar]
    E --> F[Schedule becomes published or approved]
```

### Manager flow

```mermaid
flowchart TD
    A[Manager signs in] --> B[Open department workspace]
    B --> C[Create or update monthly schedule]
    C --> D[Assign workers to shifts]
    D --> E[Review change requests]
    E --> F[Review attendance queue]
    F --> G[Export month or inspect audit trail]
```

### Worker flow

```mermaid
flowchart TD
    A[Worker signs in] --> B[View own assignments]
    B --> C{Need action?}
    C -->|No| D[Track next shift]
    C -->|Change needed| E[Submit change request]
    C -->|Check in or check out| F[Submit attendance attempt]
    E --> G[Wait for manager decision]
    F --> H[Accepted, rejected, or pending review]
```

### Scheduling and attendance relationship

```mermaid
flowchart LR
    A[Schedule period] --> B[Shift assignment]
    B --> C[Worker attendance attempt]
    C --> D{Decision}
    D -->|Accepted| E[Attendance confirmed]
    D -->|Pending| F[Manager review queue]
    D -->|Rejected| G[Attendance denied]
    E --> H[Audit trail and exports]
    F --> H
    G --> H
```

### Face-recognition attendance flow

```mermaid
flowchart TD
    A[Manager enrolls worker face] --> B[Reference embedding stored]
    C[Worker opens attendance for one assignment] --> D[Capture image]
    D --> E[Face detection]
    E --> F[Embedding generation]
    F --> G[Compare against worker template]
    G --> H{Similarity route}
    H -->|High| I[Auto accept]
    H -->|Medium| J[Manual review]
    H -->|Low| K[Auto reject]
    I --> L[Attendance attempt updated]
    J --> L
    K --> L
```

### Attendance verification sequence

```mermaid
sequenceDiagram
    participant W as Worker
    participant UI as Browser UI
    participant API as GuardyMed API
    participant CV as CV runtime
    participant DB as Database

    W->>UI: Start check-in for assigned shift
    UI->>API: POST attendance verification request
    API->>DB: Load assignment and latest template
    API->>CV: Extract embedding from capture
    CV-->>API: Probe embedding
    API->>API: Compute similarity and route decision
    API->>DB: Save attempt and match result
    API-->>UI: Accepted, rejected, or pending review
```

## Deployment

Local development runs as a single FastAPI app plus an optional Vite dev server.

- API docs: `/docs`
- mounted app: `/app`
- health check: `/health`
- frontend dev server: `http://127.0.0.1:5173/`

The production-style local build is served directly from FastAPI under `/app`.

## Demo Accounts

- manager: `manager@guardymed.local`
- worker: `worker@guardymed.local`
- password: `password123`

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite by default for local development
- Vue 3
- Vite
- PrimeVue
- NumPy
- OpenCV (optional CV runtime path)
- ONNX Runtime (optional CV runtime path)
- InsightFace (optional CV runtime path)
- pytest

## What Works Today

- manager and worker sign-in flows
- demo bootstrap for seeded data
- department and worker creation
- schedule-period creation and assignment management
- worker assignment views
- worker attendance attempts
- worker change requests
- manager review queue
- audit trail inspection
- monthly export generation
- face enrollment and face-verification demo endpoints

## CV Module Status

The attendance computer-vision module already exists in the backend and is not just a UI placeholder.

What exists today:

- a dedicated attendance CV domain module in the backend
- an optional real runtime using InsightFace + OpenCV + ONNX Runtime
- a deterministic stub runtime used by default for demo-safe local development
- enrollment and verification workflows
- similarity-based routing to `accept`, `review`, or `reject`
- API coverage and automated tests for the CV flow

Important boundary:

- the default local setting is `attendance_cv_runtime = "stub"`
- the real runtime is available as the production-path integration, not the default demo mode
- this means the MVP can honestly present a CV attendance verification module without overstating it as a hardened biometric production system

## CV Verification Pipeline

The current CV flow is small on purpose: one enrollment template, one verification attempt, one similarity score, and one routing decision.

### Current runtime model

- default runtime: deterministic stub for local demo and tests
- optional runtime: InsightFace embedding extraction through OpenCV image decoding and ONNX Runtime-backed inference

### InsightFace/OpenCV verification path

```mermaid
flowchart TD
    A[Worker or manager submits image] --> B[API receives base64 media]
    B --> C[OpenCV decodes image bytes]
    C --> D[InsightFace FaceAnalysis detects face]
    D --> E{Face found?}
    E -->|No| F[Return face_detected false]
    E -->|Yes| G[Select largest face]
    G --> H[Extract embedding]
    H --> I[Normalize embedding vector]
    I --> J[Compare with enrolled template]
    J --> K[Compute similarity score]
    K --> L{Threshold route}
    L -->|>= accept threshold| M[Accept]
    L -->|between review and accept| N[Manual review]
    L -->|< review threshold| O[Reject]
    M --> P[Persist attempt and match result]
    N --> P
    O --> P
```

### MVP CV decision model

- enrollment stores one reference embedding for the worker
- verification extracts one probe embedding from the submitted image
- cosine similarity is compared against two thresholds:
  - accept threshold
  - review threshold
- the result is routed to:
  - `accepted`
  - `pending review`
  - `rejected`

This is enough for a portfolio MVP because it demonstrates:

- a real CV module boundary
- a real runtime option
- deterministic local fallback
- a complete enrollment-to-verification workflow
- review routing integrated with the healthcare operations product

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
- `POST /attendance/cv/enrollments`
- `GET /attendance/attempts`
- `POST /attendance/attempts`
- `POST /attendance/cv/attempts`
- `GET /attendance/cv/attempts/{attempt_id}/match-result`
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

## Local Run

Backend:

```bash
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend dev:

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

Production-style local UI:

- `http://127.0.0.1:8000/app`

## Release Notes — v0.1.1

- stabilized manager and worker demo flows
- improved review queue readability
- simplified audit trail presentation
- reduced raw internal IDs in the UI
- improved attendance enrollment guards
- fixed FastAPI-mounted frontend asset paths under `/app`
- added public C4 diagram image sections to the README

Quick local run:

- `uv run uvicorn apps.api.app.main:app --reload`
- `cd apps/frontend && npm run dev` for the Vite dev server
- open `http://127.0.0.1:8000/app`
- load demo data from the session panel or call `POST /api/v1/auth/bootstrap-demo`

## Core Workflows

1. Manager creates a department, workers, a monthly schedule period, and assignments.
2. Manager enrolls a worker for attendance.
3. Worker views only their own assignments, then submits a change request or attendance attempt.
4. Manager reviews schedule items, worker requests, and attendance attempts.
5. Audit events and exports reflect the resulting operational state.

## Face Recognition Decision

The baseline verification method is embedding comparison plus explicit thresholds.

That is not a toy choice. It is the normal production baseline for face verification because the problem is:

- one known worker
- one attendance attempt
- one or a few enrolled templates
- one similarity score
- one auditable route

For this system, the important distinction is:

- verification: "is this the enrolled face for this worker?" -> embedding similarity is the right default
- identification: "who is this among all workers?" -> needs a broader search strategy and may justify pgvector or a dedicated vector index later

Better than a raw single-threshold flow does not mean replacing embeddings. It means making the verification pipeline stricter:

1. face detection and quality gate first
2. liveness or anti-spoof check
3. multi-frame capture instead of one still image
4. compare against more than one enrollment template
5. use a three-way route instead of binary pass or fail

In practice the upgrade path is:

- phase 1: one embedding comparison, accept and review thresholds
- phase 2: quality checks plus multi-template comparison
- phase 3: liveness and device-camera capture hardening

So the better option is not "something other than embeddings".
The better option is "embeddings plus better gates around them".

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
- `apps/frontend`: Vue + Vite source frontend
- `apps/web`: built frontend assets served by FastAPI
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
- a Vue frontend is built and served from the same FastAPI app
- worker and manager browser flows cover scheduling, requests, review, face enrollment, and face attendance
- CV enrollment and verification API scaffold is available behind the scheduling module
- test suite is green with `uv run --no-sync pytest`

## What Is Still Missing

The scheduling MVP exists, but these parts are still incomplete:

- real camera capture is wired only for the local browser MVP, not production hardened
- liveness detection is not implemented
- multi-template enrollment is not implemented
- manager review UI for match evidence is still lighter than a production evidence console
- deployment, storage, and async processing for media are still design-level, not production-level

## Roadmap

- harden authorization and validation edges further
- add stronger export and audit filters
- replace manual attendance evidence with a CV-assisted pipeline later
- add AI/CV modules only after the scheduling core is stable
