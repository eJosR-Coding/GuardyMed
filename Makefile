# Common tasks. Run `make help` for the list.
PORT ?= 8000
UV ?= uv
PNPM ?= pnpm

.DEFAULT_GOAL := help
.PHONY: help install demo dev test build eval clean-demo

help: ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install backend (with test tools) and frontend dependencies
	$(UV) sync --extra dev
	$(PNPM) --dir apps/frontend install --frozen-lockfile

demo: ## Run the app with demo data at http://127.0.0.1:$(PORT)/app (no Node needed; the build is committed)
	@echo "GuardyMed demo: http://127.0.0.1:$(PORT)/app  (choose Continue as manager / worker)"
	$(UV) run uvicorn apps.api.app.main:app --host 127.0.0.1 --port $(PORT)

dev: ## Backend with auto-reload; run `pnpm --dir apps/frontend dev` in a second terminal for the Vite dev server
	$(UV) run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port $(PORT)

test: ## Run the backend test suite (uses a throwaway database)
	$(UV) run --extra dev pytest -q

build: ## Build the frontend into apps/web (served by FastAPI under /app)
	$(PNPM) --dir apps/frontend build

eval: ## Evaluate face verification on LFW pairs (needs `uv sync --extra cv`, downloads ~300 MB of weights and data)
	$(UV) run --extra cv python scripts/evaluate_face_verification.py --output docs/evaluation/face_verification_lfw.json

clean-demo: ## Delete the local demo database
	rm -f guardymed.db
