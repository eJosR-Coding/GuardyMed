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

## Architecture

## C4 Diagrams

## Deployment

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite by default for local development
- vanilla HTML, CSS, and JavaScript for the mounted MVP UI
- pytest

## Domain Model

## API Design

## Repository Structure

- `apps/api`: backend API and domain logic
- `apps/web`: mounted browser MVP
- `tests`: backend and route registration tests
- `docs`: product, architecture, and research notes

## Development Workflow

## Status

Current status:

- backend Phase A scheduling core is implemented
- auth headers and role guards are implemented
- persistence is available through SQLAlchemy
- a browser MVP is available from the same FastAPI app
- test suite is green with `uv run pytest`

## Roadmap
