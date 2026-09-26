# DataSentinel demo script

Time needed: about 4 minutes. Every value shown in the UI comes from the backend. Nothing is hard-coded.

## Before presenting

Open **https://datasentinel-seven.vercel.app** and confirm **API connected** and **RCA engine: heuristic**. Reserve the shared demo during presentation, then click Reset Demo. Use the [timestamped video script](demo-video-script.md) for a 4:30 recording.

For a local alternative, run `cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1` and `cd frontend && npm run dev` in separate terminals. Open http://localhost:3000. A headless dry run is `python scripts/run_golden_path.py` from the repository root with the backend environment active. Stop any API process using the same runtime directory before that script, then restart it.

The highlighted blue button is always the next step, and the "Next:" hint explains it.

## Steps

| # | Click | What the audience sees |
|---|---|---|
| 1 | **Reset Demo** | Pipeline repo rebuilt (2 commits), 110,000 deterministic customer rows generated (seed 42). |
| 2 | **Run Healthy Pipeline** | Pipeline Status **SUCCESS**, Data Health **HEALTHY**. Country chart shows the baseline: UK 43,760 · Germany 38,710 · Italy 27,530. |
| 3 | Pick **Filter regression**, click **Inject Incident** | A developer commit lands: `refactor: simplify market filter in silver layer` (Jordan Lee). HEAD changes in the header. |
| 4 | **Run Pipeline** | **Pipeline Status: SUCCESS.** 110,000 → 43,760 rows. Data health: NOT CHECKED. *"The orchestrator is happy."* |
| 5 | **Detect** | **Data Health: CRITICAL** (pulsing) next to SUCCESS, with the banner "Silent data failure". KPI: rows −60.2%. Chart: Germany and Italy show **0 rows (missing)**. 4 critical anomalies listed. Incident `INC-0001` opened. |
| 6 | **Investigate** | 4 investigation steps complete: data evidence → git history (1 commit since baseline) → change correlation (score 1.00) → RCA. |
| 7 | (scroll) Root cause | `pipelines/customer_transform.py : line 46`, commit `refactor: simplify market filter…`, **confidence 95%**, impact of 66,240 rows and about 60% of revenue missing. Source view highlights line 46. Toggle "observed facts vs inferences". |
| 8 | (scroll) Offending change | `git show` diff: `.isin(["UK","Germany","Italy"])` → `== "UK"`. |
| 9 | **Generate Fix** | Proposed patch `INC-0001-P1` (status PROPOSED) with its diff. Nothing on disk has changed yet. |
| 10 | **Apply Fix** | Patch hash-checked, applied and committed as `fix: revert … [DataSentinel INC-0001]`. |
| 11 | **Validate** | Pipeline reruns and every check passes: Pipeline completed · Row count restored · Germany restored · Italy restored · Schema passed · Data-quality checks passed · Regression checks passed · Repository tests (6 passed). **INCIDENT INC-0001 RESOLVED.** Data Health returns to **HEALTHY**. |
| 12 | (scroll) Incident report | Full Markdown report, saved to `artifacts/incidents/INC-0001.md`. |

## Talking points

- "Green orchestrator, wrong data": the two hero tiles *are* the product.
- Detection is deterministic statistics with configurable thresholds. The LLM is only used for reasoning over evidence.
- The RCA cites a real file, line and commit, and any LLM answer is checked against the evidence.
- Remediation is proposed, then approved, then applied, then validated. It is never silent.
- Failed validation keeps the incident open. For a committed-fix recovery demonstration, use the clearly labeled local failure fixture in [screenshot-checklist.md](screenshot-checklist.md). Click **Roll Back Fix** only after failed validation with an applied patch, then generate a new fix, apply and validate. Rollback restores the pre-fix regressed source and preserves evidence; it does not itself establish recovery.
- [Timestamped video script](demo-video-script.md) and [micro demo](micro-demo.md) provide the submission storyboards.

## Encore: other incident types

Once INC-0001 is resolved, pick another type and repeat steps 3–11, or reset and capture a new baseline first:

- **Schema drift**: the `revenue` column goes missing.
- **Null explosion**: `sales_rep` nulls jump to about 25%.
- **Duplicate ingestion**: duplicate rows about 13%, rows +15%.
- **Revenue distribution shift**: mean revenue −99%.

## If something goes wrong

- **API offline**: verify connectivity; for the hosted demo consult deployment health checks, and locally start the backend.
- **Any 409 error**: the message explains the workflow state. **Reset Demo** always recovers.
- **LLM provider down**: RCA falls back to the deterministic engine automatically, and the root-cause card shows the engine note.
