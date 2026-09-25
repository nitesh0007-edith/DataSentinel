# AGENTS.md

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

## Do not

- add Kubernetes, message queues, microservices or a database;
- replace deterministic checks with LLM calls;
- auto-apply patches or widen the patch path/suffix allowlist;
- run git through a shell or pass unvalidated refs/paths to git;
- hard-code RCA results in the UI.
