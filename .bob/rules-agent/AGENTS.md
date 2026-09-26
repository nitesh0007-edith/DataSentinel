# Project Coding Rules (Non-Obvious Only)

- Every Python file must start with `from __future__ import annotations` — no exceptions.
- Use `write_text_atomic()` from `app.core.state` for any file write that must be crash-safe (state, patches, profiles).
- `get_settings()` is `@lru_cache` — call `get_settings.cache_clear()` before AND after any test that sets env vars via monkeypatch.
- All domain errors must be `DataSentinelError` subclasses (`ConflictError`, `NotFoundError`, `UnsafeOperationError`). The FastAPI handler in `app.main` maps them to HTTP status codes automatically.
- Git must only be accessed via `GitRepository` in `app.investigation.git_analyzer`. Never `subprocess.run(["git", ...])`. Refs go through `validate_ref()`, repo-relative paths through `resolve_in_repo()`.
- LLM is optional (`None` = heuristic mode). All code that uses LLM must fall back gracefully to the heuristic path. Tests must pass with `LLM_PROVIDER=heuristic` and no network.
- The monitored repo lives at `settings.pipeline_repo` (`workspace/pipeline_repo`). Never edit it directly — it is rebuilt by `reset_workspace()`. Changes to pipeline code go via `apply_patch()` only.
- Patch application is single-entry: `app.remediation.patch_service.apply_patch()`. The `ALLOWED_SUFFIXES = {".py"}` constant is a security boundary — never widen it.
- Detection is deterministic (pandas-based in `app.detection.anomaly_engine`). Never add LLM calls to metric computation or anomaly scoring.
- Frontend: all components use `"use client"`. API calls go through the `api` singleton in `lib/api.ts` — never raw `fetch`. Errors are `ApiError` with `.status` and `.message`.
- Frontend `@/*` path alias maps to `frontend/*`, not the repo root.
- `npm run lint` is `tsc --noEmit` only. There is no ESLint. Passing TypeScript is the only lint gate.
- `npm run build` uses `next build --webpack` (explicit flag in `package.json`).
- Demo scripts in `scripts/` must be run from the project root (`python scripts/xxx.py`), not from inside `scripts/`; they depend on `_bootstrap.py` for sys.path setup.
