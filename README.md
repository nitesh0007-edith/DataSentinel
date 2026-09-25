# DataSentinel

**An autonomous data reliability engineer.**

> Pipeline status: **SUCCESS** ✅  ·  Data health: **CRITICAL** 🔴

## The problem

Orchestrators like Airflow, Dagster and dbt Cloud tell you whether your code *ran*, not whether your data is *right*. A pipeline can finish green while it silently produces wrong data. Common causes:

- a filter that was narrowed by accident (whole markets vanish)
- schema drift (a renamed column breaks every consumer)
- null explosions, duplicate ingestion, unit bugs that shift distributions
- "harmless" refactors of transformation code

Nobody gets paged, and the dashboards are wrong until a human notices.

## The solution

DataSentinel watches pipeline outputs and closes the loop:

```
DETECT  →  INVESTIGATE  →  ROOT CAUSE  →  PROPOSE FIX  →  APPLY (approved)  →  VALIDATE  →  REPORT
```

1. **Profiles** every run: row counts, nulls, duplicates, dtypes, numeric statistics and category frequencies.
2. **Detects** anomalies against a healthy baseline using deterministic, explainable rules. The math is never done by an LLM.
3. **Investigates.** It collects git history since the last healthy run and correlates diff hunks with the anomalies.
4. **Explains** the root cause, citing file, line and commit, with a confidence score. Observed facts are kept separate from inferences. An optional LLM reasons over the same evidence package, and its output is grounded: any file, line or commit that isn't in the evidence is rejected.
5. **Proposes** a patch (a reverse of the offending hunk). The patch is shown as a diff and only applied when someone clicks Apply.
6. **Validates** by rerunning the pipeline, re-profiling, comparing to the baseline and running the repository's tests. The incident becomes **RESOLVED** only if every check passes.
7. **Reports** the incident as a Markdown write-up under `artifacts/incidents/`.

## Screenshots

_Placeholder: add `docs/screenshots/critical.png` (SUCCESS vs CRITICAL) and `docs/screenshots/resolved.png` after running the demo._

## Architecture

```
          Next.js dashboard (frontend/)
                    │  REST
                    ▼
          FastAPI (backend/app/api)
                    │
          DataSentinelService (services/workflow.py) ── JSON state (artifacts/state.json)
   ┌──────────┬──────────┼───────────┬─────────────┬────────────┐
pipeline   profiling  detection  investigation  remediation  validation → reporting
generator  profiler   rules      git_analyzer   patch_gen    validator    incident_report
runner                engine     evidence       patch_svc
injector                         rca_agent ── llm/ (heuristic | anthropic | openai)
   │
   ▼
workspace/pipeline_repo   ← a real git repo holding the monitored transformation code
```

**Why a separate `workspace/pipeline_repo`?** DataSentinel needs real git evidence (`git log`, `git show`, diffs), and injected regressions and fixes need to be real commits. Committing broken code into DataSentinel's own history on every demo would pollute your branches. So the monitored pipeline lives in a small git repo that is rebuilt from `backend/app/pipeline/template_repo/` on every reset. That keeps the demo deterministic and your repo clean.

More detail is in [docs/architecture.md](docs/architecture.md).

## Setup

Prerequisites: Python 3.11+, Node 20+, and `git` on PATH.

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs are served at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                          # http://localhost:3000
```

> **Tip:** if the project lives in a synced folder (Google Drive, Dropbox, iCloud), `node_modules/` and the demo's git workspace will sync thousands of small files. Clone it to a normal local directory, or set `DATASENTINEL_WORKSPACE_DIR` to a local path.

### Environment variables

Copy `.env.example` to `.env` in the repo root. Everything is optional:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `heuristic` | `heuristic` (deterministic, offline), `anthropic`, or `openai` |
| `LLM_MODEL` | provider default | Model override |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | | Keys for the chosen provider |
| `DATASENTINEL_HOME` | repo root | Root for `data/`, `artifacts/`, `workspace/` |
| `DATASENTINEL_WORKSPACE_DIR` | `$HOME/workspace` | Location of the monitored pipeline repo |
| `DATASENTINEL_DEFAULT_ROWS` / `_SEED` | `110000` / `42` | Synthetic data size and seed |
| `DATASENTINEL_THRESHOLDS` | see `core/config.py` | JSON override of detection thresholds |

If an LLM provider is configured but unreachable or returns invalid output, DataSentinel falls back to the deterministic engine and records why in `engine_notes`.

## Running the demo

Use the UI; exact steps are in [docs/demo.md](docs/demo.md). You can also run it headless:

```bash
python scripts/run_golden_path.py                       # filter_regression, end to end
python scripts/run_golden_path.py --type schema_drift   # any incident type
```

Individual steps:

```bash
python scripts/reset_demo.py --baseline      # reset + healthy baseline
python scripts/inject_incident.py filter_regression
python scripts/run_pipeline.py --detect      # prints Pipeline Status = SUCCESS, Data Health = CRITICAL
```

## Incident types

| Type | Injected code change | Detected by |
|---|---|---|
| `filter_regression` (P0) | `country.isin(["UK","Germany","Italy"])` → `country == "UK"` | row count −60%, Germany/Italy disappear, category shift |
| `null_explosion` | `sales_rep` masked for Enterprise accounts | null-rate drift on `sales_rep` |
| `duplicate_ingestion` | replay batch re-appended in bronze | duplicate-rate drift, row count +15% |
| `schema_drift` | `revenue` renamed to `revenue_amount` | missing and unexpected columns |
| `revenue_shift` | revenue divided by 100 | numeric mean/median drift |

In every case the pipeline still reports **SUCCESS**.

## API overview

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness and configured RCA engine |
| GET | `/api/state` | Everything the dashboard needs |
| POST | `/api/demo/reset` | Reset data, artifacts and pipeline repo; regenerate data |
| POST | `/api/data/generate` | `{rows, seed}`: regenerate raw data |
| POST | `/api/pipeline/run` | `{set_baseline}`: run RAW→BRONZE→SILVER→GOLD |
| GET | `/api/pipeline/runs` | Run history |
| GET | `/api/incidents/types` | Injectable incident scenarios |
| POST | `/api/incidents/inject` | `{type}`: commit a regression to the pipeline repo |
| POST | `/api/incidents/detect` | Compare the latest run with the baseline; opens an incident on WARNING/CRITICAL |
| GET | `/api/incidents[/{id}]` | Incidents |
| POST | `/api/incidents/{id}/investigate` | Evidence package and RCA |
| POST | `/api/incidents/{id}/fix` | Propose a patch (no file changes) |
| POST | `/api/incidents/{id}/reject` | Reject the proposed patch |
| POST | `/api/incidents/{id}/apply` | Apply the approved patch (hash-checked, repo-confined, committed) |
| POST | `/api/incidents/{id}/validate` | Rerun, re-profile, compare and test; RESOLVED only on full pass |
| GET | `/api/incidents/{id}/report` | Markdown incident report |

Errors return `{"detail": "..."}` with 400/403/404/409 status codes.

## Testing

```bash
cd backend
pytest
```

The suite covers data generation, profiling, every detection rule, the filter incident, git and path safety, heuristic RCA, LLM grounding and fallback (with a fake provider, no API keys), the patch safety checks, validation failing without a fix, the API golden path, and end-to-end resolution of all five incident types.

## Safety design

- **Git:** allowlisted subcommands only, argument lists (never a shell), timeouts, validated revisions and paths, and host git hooks disabled.
- **Patches:** only proposed patches can be applied, and only after explicit approval. Targets must resolve inside the pipeline repo (not `.git`) and be `.py` files. The file hash must match what the patch was generated against, and the stored proposed content is hash-verified. Every applied patch is committed, and the original is backed up in `artifacts/patches/`.
- **LLM:** receives only the evidence package, never raw repository access. Its answer is grounded against that evidence, and deterministic logic remains the source of truth for the numbers.
- **Secrets:** read only from the environment. `.env` is gitignored.

## Hackathon context

Built as a working vertical slice. The priority was one flawless end-to-end story (filter regression → SUCCESS but wrong → CRITICAL → root cause → fix → validation → RESOLVED), then breadth across the remaining incident types. State is kept in JSON files and there is no database or other infrastructure. See `DATASENTINEL_BUILD_PLAN_v2.md` for the full plan and the Codex and Bob hardening phases.
