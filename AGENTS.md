# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project

DataSentinel is an autonomous data reliability engineer. It detects silent data-pipeline failures, investigates data and git evidence, identifies a likely root cause, proposes a safe fix and validates recovery.

## Critical demo (must never break)

A filter regression (`country.isin(["UK","Germany","Italy"])` → `country == "UK"`) makes Germany and Italy disappear while the pipeline still reports SUCCESS. DataSentinel must detect it as CRITICAL, find `pipelines/customer_transform.py` and the offending commit, propose the reverse patch, and validate to RESOLVED.

Check it with `python scripts/run_golden_path.py` and `cd backend && pytest`.

## Design principles

1. Deterministic detection before LLM reasoning. Never compute metrics with an LLM.
2. Evidence-grounded RCA. The LLM sees only the `EvidencePackage`, and its output is grounded (`rca_agent.ground_llm_result`).
3. Safe remediation: propose, approve, apply (hash-checked, confined to the pipeline repo, committed), then validate.
4. Reproducible demo: seeded data, template repo rebuilt on reset.
5. Clear separation: pipeline / profiling / detection / investigation / remediation / validation / reporting.
6. No secrets in the repo. Tests must not need external LLM APIs (use a fake `LLMProvider`).

## Layout

- `backend/app/services/workflow.py`: the state machine. Start here.
- `backend/app/core/config.py`: all thresholds and paths.
- `backend/app/pipeline/template_repo/`: source of the monitored repo (`workspace/pipeline_repo` is generated; never edit it by hand).
- `frontend/app/page.tsx`: the dashboard. Components are in `frontend/components/`.

## Commands

### Backend
```bash
cd backend && uvicorn app.main:app --reload   # dev server on :8000
cd backend && pytest                          # all tests
cd backend && pytest tests/test_detection.py  # single test file
cd backend && pytest tests/test_detection.py::test_name  # single test
```

### Frontend
```bash
cd frontend && npm run dev    # dev server on :3000
cd frontend && npm run lint   # TypeScript type-check only (tsc --noEmit); no ESLint
cd frontend && npm run build  # next build --webpack (uses --webpack flag explicitly)
```

### Demo scripts (run from project root)
```bash
python scripts/reset_demo.py --baseline   # full reset + baseline capture
python scripts/run_golden_path.py         # end-to-end demo validation
python scripts/inject_incident.py         # inject a regression into pipeline repo
```
Scripts import from `app.*` via `_bootstrap.py`; always run from repo root, not from `scripts/`.

## Code style — Backend (Python)

- All files begin with `from __future__ import annotations`.
- Pydantic v2 (`BaseModel`, `BaseSettings`) for all models and config; `pydantic-settings` for env-based config.
- Settings use env prefix `DATASENTINEL_`; LLM keys are unprefixed (`ANTHROPIC_API_KEY`, `LLM_PROVIDER`).
- `get_settings()` is `@lru_cache`; call `get_settings.cache_clear()` in tests when patching env vars.
- Domain errors: raise `ConflictError` (409), `NotFoundError` (404), `UnsafeOperationError` (403) from `app.core.errors`; all inherit `DataSentinelError`. The API handler maps these automatically.
- Loggers: `get_logger("module_name")` from `app.core.logging`; never use `print()` in library code.
- Atomic file writes: use `write_text_atomic()` from `app.core.state` — never bare `path.write_text()` for state/patch files.
- Git access: only via `GitRepository` from `app.investigation.git_analyzer`; never `subprocess` or shell. Refs validated with `validate_ref()`; paths with `validate_repo_path()` or `resolve_in_repo()`.
- Tests use `tmp_path` + `monkeypatch.setenv("DATASENTINEL_HOME", ...)` + `get_settings.cache_clear()` (see `conftest.py`). Set `LLM_PROVIDER=heuristic` to avoid real LLM calls.
- Patch allowlist: only `.py` files; defined as `ALLOWED_SUFFIXES` in `patch_service.py` — do not widen it.

## Code style — Frontend (TypeScript / Next.js 16 / React 19)

- `@/*` maps to `frontend/*` (tsconfig paths); use it for all internal imports.
- `"use client"` directive is required on all interactive components (all current panels/pages).
- Lint is TypeScript-only (`tsc --noEmit`); there is no ESLint config.
- Tailwind CSS v4 (PostCSS plugin); no CSS modules or separate style files.
- API calls go through `api` object in `lib/api.ts`; errors surface as `ApiError` with `.status`.
- Backend URL via `NEXT_PUBLIC_API_URL` env var (default `http://localhost:8000`) in `frontend/.env.local`.
- All domain types live in `frontend/types/index.ts` — add new API types there.
- Components are grouped into four flat files: `ui.tsx`, `panels.tsx`, `charts.tsx`, `ControlBar.tsx` — no subdirectory nesting.

## Do not

- add Kubernetes, message queues, microservices or a database;
- replace deterministic checks with LLM calls;
- auto-apply patches or widen the patch path/suffix allowlist;
- run git through a shell or pass unvalidated refs/paths to git;
- hard-code RCA results in the UI.
