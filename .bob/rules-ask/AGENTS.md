# Project Documentation Context (Non-Obvious Only)

- `workspace/pipeline_repo` is a generated git repo rebuilt on every demo reset. It is NOT part of the DataSentinel source tree — never reference it as source code, never suggest editing it.
- `backend/app/pipeline/template_repo/` is the canonical source for the monitored pipeline code; `workspace/` is derived.
- The RCA output is always "grounded" — the LLM result is post-processed by `rca_agent.ground_llm_result()` to strip any file/commit references not present in the evidence package. RCA is NOT a raw LLM completion.
- There are two parallel env var systems: `DATASENTINEL_*` prefixed vars for backend settings, and `NEXT_PUBLIC_*` for frontend. LLM keys (`ANTHROPIC_API_KEY`, `LLM_PROVIDER`) intentionally skip the prefix (see `config.py` `AliasChoices`).
- The frontend is Next.js 16 / React 19 — both are current pre-release versions; APIs differ from stable 14/18 training data.
- `frontend/CLAUDE.md` is just `@AGENTS.md` — it delegates to `frontend/AGENTS.md` (Next.js auto-generated agent rules).
- Detection thresholds can be overridden at runtime via `DATASENTINEL_THRESHOLDS={"row_count_critical": 0.3}` JSON env var — no code change needed.
- State is persisted to `artifacts/state.json` as JSON (no database). `StateStore` in `app.core.state` owns all reads/writes.
