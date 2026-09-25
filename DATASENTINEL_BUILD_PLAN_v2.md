# DataSentinel
## Autonomous Data Reliability Engineer

> **Tagline:** Your pipeline can succeed while your data fails. DataSentinel catches what orchestration tools miss.

---

# 1. Project Overview

**DataSentinel** is an AI-assisted incident detection, root-cause analysis, and remediation platform for data pipelines.

Most orchestration tools can tell engineers whether a pipeline technically succeeded or failed. However, a pipeline can complete successfully while silently producing incorrect data because of issues such as:

- unexpected row-count drops
- schema drift
- duplicate ingestion
- null explosions
- distribution drift
- missing categories or partitions
- incorrect filters
- broken transformations
- bad joins
- accidental code changes
- configuration mistakes

DataSentinel focuses on these **silent data failures**.

It continuously compares the current pipeline output against expected historical behaviour, detects anomalies, investigates the repository and pipeline context, identifies likely root causes, proposes a code fix, validates the change, and generates an incident report.

The intended hackathon workflow is:

```text
Claude Code
    ↓
Build the main MVP quickly
    ↓
Codex
    ↓
Test, debug, refactor, and harden the MVP
    ↓
IBM Bob 2.0
    ↓
Understand the repository, plan improvements,
use subagents, implement improvements,
review changes, and validate the final solution
```

---

# 2. Core Hackathon Story

The demo should tell one simple story:

```text
A data pipeline technically succeeds.

But the output is wrong.

DataSentinel detects the anomaly.

DataSentinel investigates:
- data profile
- schema
- pipeline logs
- repository changes
- Git diff
- validation rules

It identifies the likely root cause.

It proposes a patch.

The patch is validated.

The data pipeline becomes healthy again.
```

The project is not only an anomaly detector.

It is an **AI Data Reliability Engineer**.

---

# 3. Primary Demo Scenario

Use a simulated customer analytics pipeline.

Healthy pipeline:

```text
RAW
  ↓
BRONZE
  ↓
SILVER
  ↓
GOLD
```

Example data:

```text
customer_id
country
product
revenue
segment
sales_rep
event_date
provider_id
```

Supported countries:

```text
UK
Germany
Italy
```

Healthy transformation:

```python
df = df[df["country"].isin(["UK", "Germany", "Italy"])]
```

Injected bug:

```python
df = df[df["country"] == "UK"]
```

The pipeline still completes.

However:

```text
Rows Yesterday: 120,000
Rows Today:      39,800
Change:          -66.8%

Germany records: 40,100 → 0
Italy records:   40,100 → 0
```

DataSentinel should detect the anomaly and identify the code change that caused it.

---

# 4. Additional Demo Incidents

The MVP should support multiple predefined incident types.

## Incident A — Filter Regression

```text
Expected:
UK + Germany + Italy

Actual:
UK only
```

Detection signals:

- row count drop
- category disappearance
- revenue drop
- geographic distribution shift

---

## Incident B — Null Explosion

Healthy:

```text
provider_id null rate = 0.3%
```

Broken:

```text
provider_id null rate = 24.8%
```

Detection signals:

- null-rate anomaly
- potential upstream mapping failure

---

## Incident C — Duplicate Ingestion

Healthy:

```text
100,000 records
```

Broken:

```text
198,000 records
```

Detection signals:

- duplicate ratio
- unexpected row-count increase
- duplicate primary keys

---

## Incident D — Schema Drift

Healthy:

```text
customer_id: STRING
```

Broken:

```text
customer_id: INTEGER
```

Detection signals:

- schema mismatch
- downstream join risk

---

## Incident E — Revenue Distribution Shift

Healthy:

```text
mean revenue ≈ £280
```

Broken:

```text
mean revenue ≈ £62
```

Detection signals:

- numeric distribution drift
- suspicious transformation or currency error

---

# 5. MVP Features

The MVP must contain the following modules.

## 5.1 Synthetic Data Generator

Generate realistic customer transaction data.

Requirements:

- deterministic seed support
- configurable number of rows
- multiple countries
- revenue distribution
- customer segments
- provider IDs
- event dates
- product categories

Output:

```text
data/baseline/
data/current/
```

Preferred formats:

```text
CSV initially
Parquet optionally
```

---

## 5.2 Pipeline Simulator

Simulate:

```text
raw → bronze → silver → gold
```

Each pipeline run should produce:

- transformed dataset
- run metadata
- logs
- row counts
- schema snapshot
- quality metrics
- timestamp
- Git commit reference if available

Example:

```json
{
  "run_id": "run_20260925_001",
  "status": "SUCCESS",
  "rows_input": 120000,
  "rows_output": 39800,
  "duration_seconds": 4.8,
  "commit": "a82f1cb"
}
```

---

## 5.3 Incident Injector

Provide a UI control or CLI command to inject incidents.

Example:

```bash
python scripts/inject_incident.py --type filter_regression
```

Supported values:

```text
filter_regression
null_explosion
duplicate_ingestion
schema_drift
revenue_shift
```

The injector should change either:

- transformation code
- source data
- configuration

depending on incident type.

---

## 5.4 Data Profiler

For every pipeline run calculate:

### Dataset level

- row count
- column count
- duplicate count
- duplicate percentage

### Column level

- datatype
- null count
- null percentage
- unique count
- min
- max
- mean
- median where relevant

### Categorical

- top values
- category frequencies

### Numeric

- mean
- standard deviation
- min
- max
- quantiles

Store profile results as JSON.

Example:

```text
artifacts/profiles/run_001.json
artifacts/profiles/run_002.json
```

---

# 6. Anomaly Detection Engine

Do not overcomplicate the first version.

Use deterministic/statistical checks.

## Suggested Rules

### Row Count Change

```python
pct_change = abs(current_rows - baseline_rows) / baseline_rows
```

Example thresholds:

```text
< 10%   = normal
10–25%  = warning
> 25%   = critical
```

---

### Null Rate Drift

```python
null_delta = current_null_rate - baseline_null_rate
```

---

### Schema Drift

Compare:

```text
column name
datatype
presence
```

---

### Duplicate Drift

Compare duplicate percentage against baseline.

---

### Categorical Drift

Detect:

- missing expected values
- new unexpected values
- large frequency changes

---

### Numeric Drift

Initially use:

- percentage change in mean
- z-score
- IQR checks

Optional:

- Kolmogorov-Smirnov test
- PSI
- Jensen-Shannon divergence

---

# 7. Incident Severity

Implement:

```text
INFO
WARNING
CRITICAL
```

Example scoring:

```python
anomaly_score = (
    0.30 * row_count_score +
    0.25 * null_score +
    0.20 * schema_score +
    0.15 * distribution_score +
    0.10 * duplicate_score
)
```

Suggested mapping:

```text
0.00–0.29 → INFO
0.30–0.59 → WARNING
0.60–1.00 → CRITICAL
```

Keep thresholds configurable.

---

# 8. Root Cause Analysis Engine

The RCA engine receives:

```text
current profile
baseline profile
pipeline logs
schema diff
anomaly summary
Git diff
recent commits
relevant source files
```

The LLM should reason over this evidence.

Expected output:

```json
{
  "incident_type": "filter_regression",
  "severity": "CRITICAL",
  "likely_root_cause": "Country filter was changed from a multi-country filter to UK-only.",
  "file": "pipelines/customer_transform.py",
  "line": 42,
  "confidence": 0.94,
  "impact": "Germany and Italy records were excluded.",
  "recommended_fix": "Restore the original multi-country filter."
}
```

Important:

**Do not let the LLM invent evidence.**

The RCA prompt must instruct the model to:

- use only provided repository/data evidence
- cite filenames
- cite lines where possible
- separate observed facts from inference
- provide a confidence score
- say "insufficient evidence" if root cause is unclear

---

# 9. Git Investigation Module

Implement a simple Git analyser.

Commands may include:

```bash
git log --oneline -10
git diff HEAD~1 HEAD
git show <commit>
```

Extract:

- changed files
- changed lines
- commit messages
- recent commits

Expose results to the RCA engine.

Later IBM Bob can extend this repository understanding.

---

# 10. Fix Generation

Once root cause is confirmed, generate a patch proposal.

Example:

```diff
- df = df[df["country"] == "UK"]
+ df = df[df["country"].isin(["UK", "Germany", "Italy"])]
```

Do not auto-apply immediately.

UI should show:

```text
Proposed Fix

[View Diff]

[Apply Fix]

[Reject]
```

---

# 11. Validation Engine

After a patch is applied:

1. rerun pipeline
2. regenerate profile
3. compare against baseline
4. run tests
5. verify anomaly resolved

Example result:

```text
Validation Result

✓ Pipeline completed
✓ Row count restored
✓ Germany records restored
✓ Italy records restored
✓ Null checks passed
✓ Schema checks passed
✓ Regression tests passed

INCIDENT RESOLVED
```

---

# 12. Incident Report Generator

Generate a Markdown incident report.

Example:

```text
Incident ID
Timestamp
Severity
Symptoms
Detected anomalies
Root cause
Affected file
Affected commit
Impact
Patch
Validation result
Resolution status
```

Save under:

```text
artifacts/incidents/
```

---

# 13. Dashboard

Recommended frontend:

```text
Next.js
React
TypeScript
Tailwind
```

Alternative for faster delivery:

```text
Streamlit
```

Preferred hackathon version:

**Next.js frontend + FastAPI backend**

because the visual demo will look stronger.

---

# 14. Dashboard Layout

Home page:

```text
┌──────────────────────────────────────────────────────────┐
│                     DataSentinel                         │
│            Autonomous Data Reliability Engineer         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ Pipeline Health                         🔴 CRITICAL       │
│                                                          │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│ │ Rows       │ │ Null Rate  │ │ Schema     │             │
│ │ ▼ 66.8%    │ │ ▲ 0.1%     │ │ Healthy    │             │
│ └────────────┘ └────────────┘ └────────────┘             │
│                                                          │
│ Anomaly Timeline                                         │
│ [ chart ]                                                │
│                                                          │
│ Investigation                                            │
│ ✓ Row Count Analysis                                     │
│ ✓ Distribution Analysis                                  │
│ ✓ Git Diff Analysis                                      │
│ ✓ Root Cause Analysis                                    │
│                                                          │
│ Root Cause                                               │
│ customer_transform.py : line 42                          │
│ Country filter changed to UK-only                        │
│                                                          │
│ Confidence: 94%                                          │
│                                                          │
│ [ VIEW DIFF ]  [ GENERATE FIX ]  [ VALIDATE ]            │
└──────────────────────────────────────────────────────────┘
```

---

# 15. Suggested Architecture

```text
                        ┌────────────────────┐
                        │     Next.js UI     │
                        └─────────┬──────────┘
                                  │
                                  ▼
                        ┌────────────────────┐
                        │      FastAPI       │
                        └─────────┬──────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
 Pipeline Engine           Detection Engine           RCA Engine
        │                         │                         │
        ▼                         ▼                         ▼
 Synthetic Data            Data Profiler             LLM Provider
 Incident Injector         Schema Diff               Git Analyzer
 Pipeline Runner           Drift Checks              Evidence Pack
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                                  ▼
                         Validation Engine
                                  │
                                  ▼
                         Incident Reporter
```

---

# 16. Suggested Repository Structure

```text
datasentinel/
│
├── README.md
├── AGENTS.md
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── pipelines.py
│   │   │   ├── incidents.py
│   │   │   ├── investigation.py
│   │   │   └── validation.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logging.py
│   │   │
│   │   ├── pipeline/
│   │   │   ├── generator.py
│   │   │   ├── runner.py
│   │   │   ├── transformations.py
│   │   │   └── incident_injector.py
│   │   │
│   │   ├── profiling/
│   │   │   ├── profiler.py
│   │   │   ├── schema.py
│   │   │   └── statistics.py
│   │   │
│   │   ├── detection/
│   │   │   ├── anomaly_engine.py
│   │   │   ├── rules.py
│   │   │   └── severity.py
│   │   │
│   │   ├── investigation/
│   │   │   ├── git_analyzer.py
│   │   │   ├── evidence_builder.py
│   │   │   ├── rca_agent.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── remediation/
│   │   │   ├── patch_generator.py
│   │   │   └── patch_service.py
│   │   │
│   │   ├── validation/
│   │   │   ├── validator.py
│   │   │   └── regression.py
│   │   │
│   │   └── reporting/
│   │       └── incident_report.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── types/
│   └── package.json
│
├── data/
│   ├── baseline/
│   ├── current/
│   └── generated/
│
├── artifacts/
│   ├── profiles/
│   ├── incidents/
│   ├── patches/
│   └── logs/
│
├── scripts/
│   ├── generate_data.py
│   ├── run_pipeline.py
│   ├── inject_incident.py
│   └── reset_demo.py
│
└── docs/
    ├── architecture.md
    ├── demo.md
    └── screenshots/
```

---

# 17. Backend API

Suggested endpoints.

## Health

```text
GET /health
```

---

## Generate Dataset

```text
POST /api/data/generate
```

Body:

```json
{
  "rows": 100000,
  "seed": 42
}
```

---

## Run Pipeline

```text
POST /api/pipeline/run
```

---

## Get Pipeline Runs

```text
GET /api/pipeline/runs
```

---

## Inject Incident

```text
POST /api/incidents/inject
```

Body:

```json
{
  "type": "filter_regression"
}
```

---

## Detect Anomalies

```text
POST /api/incidents/detect
```

---

## Investigate Incident

```text
POST /api/incidents/{incident_id}/investigate
```

---

## Generate Fix

```text
POST /api/incidents/{incident_id}/fix
```

---

## Apply Fix

```text
POST /api/incidents/{incident_id}/apply
```

---

## Validate Fix

```text
POST /api/incidents/{incident_id}/validate
```

---

# 18. LLM Abstraction

Do not hard-wire the product to one model.

Create:

```python
class LLMProvider:
    def generate(self, messages):
        ...
```

Implement provider wrappers if time allows.

Possible providers:

```text
OpenAI
Anthropic
IBM-supported model / endpoint later
local mock provider for testing
```

Environment variables:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LLM_PROVIDER=
LLM_MODEL=
```

Never commit secrets.

---

# 19. Development Phases

---

# PHASE 1 — CLAUDE CODE

## Goal

Claude Code should build the functional MVP quickly.

Claude owns:

- architecture implementation
- backend
- frontend
- synthetic data pipeline
- anomaly engine
- initial RCA integration
- Git investigation
- remediation workflow
- dashboard
- documentation

Claude should **not** spend large amounts of time on exhaustive tests.

Codex handles that in Phase 2.

---

# 20. Claude Code — Initial Prompt

Copy the following prompt into Claude Code from the root of the new repository.

```text
You are the lead software engineer for a hackathon project called DataSentinel.

DataSentinel is an Autonomous Data Reliability Engineer.

The core problem:

Data pipelines often technically succeed while silently producing incorrect data because of bad filters, schema drift, null explosions, duplicate ingestion, distribution shifts, broken transformations, or accidental code changes.

DataSentinel must detect these silent failures, investigate the data and repository, identify a likely root cause, propose a patch, rerun validation, and generate an incident report.

Build a production-style but hackathon-scoped MVP.

TECH STACK

Frontend:
- Next.js
- React
- TypeScript
- Tailwind CSS

Backend:
- Python
- FastAPI
- pandas initially
- pytest
- Pydantic

AI:
- provider abstraction
- support OpenAI or Anthropic via environment variables
- do not hard-wire business logic to one model

PROJECT REQUIREMENTS

1. Synthetic customer-data generator.
Columns:
- customer_id
- country
- product
- revenue
- segment
- sales_rep
- provider_id
- event_date

Countries:
- UK
- Germany
- Italy

2. Pipeline simulator:
raw → bronze → silver → gold

3. Incident injector supporting:
- filter_regression
- null_explosion
- duplicate_ingestion
- schema_drift
- revenue_shift

4. Data profiler:
- row count
- duplicates
- null rates
- schema
- categorical frequency
- numeric summary statistics

5. Anomaly detection:
- row-count change
- null-rate drift
- schema drift
- duplicates
- categorical drift
- numeric drift

6. Severity:
INFO
WARNING
CRITICAL

7. Git analyser using safe subprocess calls:
- recent commits
- diff
- changed files
- changed lines

8. Evidence builder combining:
- data anomalies
- schemas
- pipeline logs
- Git diff
- recent commits
- relevant source snippets

9. RCA agent.

The RCA agent must:
- reason only from provided evidence
- separate observed evidence from inference
- identify likely file/line when possible
- provide confidence
- state insufficient evidence when appropriate
- return structured JSON

10. Fix generator:
produce a proposed patch/diff.

11. Validation:
- rerun pipeline
- regenerate profile
- compare with baseline
- run regression checks

12. Incident report:
Markdown output saved to artifacts/incidents/

13. Dashboard showing:
- pipeline health
- row count change
- null-rate changes
- schema status
- anomaly timeline
- investigation steps
- root cause
- confidence
- Git diff
- suggested fix
- validation result

14. Demo workflow:

RESET DEMO
→ RUN HEALTHY PIPELINE
→ INJECT FILTER REGRESSION
→ RUN PIPELINE
→ PIPELINE RETURNS SUCCESS
→ DATASENTINEL DETECTS CRITICAL INCIDENT
→ INVESTIGATE
→ ROOT CAUSE FOUND
→ GENERATE FIX
→ APPLY
→ VALIDATE
→ INCIDENT RESOLVED

IMPORTANT ENGINEERING RULES

- Keep modules clean and separated.
- Prefer deterministic logic over LLM calls where possible.
- LLM is for reasoning/explanation, not basic statistics.
- Never expose API keys.
- Add .env.example.
- Add clear logging.
- Add type hints.
- Add Pydantic models.
- Add graceful errors.
- Add README with run instructions.
- Avoid unnecessary infrastructure.
- No Kubernetes.
- No microservices.
- No external database unless absolutely necessary.
- Store demo state locally using JSON/files.
- Keep setup simple enough for judges to run locally.
- Make the UI visually impressive and enterprise-oriented.
- Do not overengineer.

IMPLEMENTATION APPROACH

First inspect the repository.

Then:
1. create a concise architecture plan
2. create the repository structure
3. implement backend core
4. implement synthetic data generator
5. implement pipeline simulator
6. implement incident injector
7. implement profiling
8. implement anomaly detection
9. implement Git investigation
10. implement RCA abstraction
11. implement remediation and validation
12. implement frontend dashboard
13. connect frontend/backend
14. add demo/reset scripts
15. add initial tests for critical paths
16. run everything locally
17. fix runtime errors
18. update README

Do not stop after scaffolding.
Continue until a working vertical slice exists.

The first successful vertical slice must support the filter_regression demo from start to finish.

Before making major architectural decisions, explain them briefly.

Begin by proposing the implementation plan and then start building.
```

---

# 21. Claude Code Milestone 1

Expected result:

```text
✓ repository created
✓ backend runs
✓ frontend runs
✓ healthy synthetic pipeline runs
✓ profile generated
```

Commit:

```bash
git add .
git commit -m "feat: build DataSentinel foundation"
```

---

# 22. Claude Code Milestone 2 Prompt

```text
Continue DataSentinel.

We now need the end-to-end FILTER REGRESSION demo.

Implement and verify:

1. Generate healthy data with UK, Germany, and Italy.
2. Run healthy pipeline.
3. Save baseline profile.
4. Inject a filter bug that causes only UK records to remain.
5. Run the pipeline again.
6. Pipeline should still report SUCCESS.
7. DataSentinel must detect:
   - major row-count drop
   - Germany disappearance
   - Italy disappearance
   - distribution drift
8. Create a CRITICAL incident.
9. Git analyser must inspect the relevant transformation change.
10. Evidence builder must connect the anomaly and Git diff.
11. RCA must identify the country filter as likely root cause.
12. UI must display:
   - incident
   - evidence
   - likely file
   - root cause
   - confidence
13. Generate a proposed patch.
14. Apply the patch safely.
15. Rerun pipeline.
16. Confirm Germany and Italy are restored.
17. Mark incident RESOLVED.

Do not simulate the final result with hard-coded UI text.
The UI must display backend-generated results.

Run the application and fix errors before finishing.
```

---

# 23. Claude Code Milestone 3 Prompt

```text
Polish DataSentinel for a hackathon demo.

Focus on:

- enterprise-grade dashboard appearance
- pipeline health summary
- incident severity badges
- clear anomaly visualisation
- investigation timeline
- root-cause card
- confidence meter
- code diff viewer
- remediation controls
- validation results
- loading states
- errors
- demo reset button

Add support for the remaining predefined incidents:

- null_explosion
- duplicate_ingestion
- schema_drift
- revenue_shift

Do not sacrifice stability for extra features.

Make FILTER REGRESSION the most polished scenario.

Update README and docs/demo.md with exact demo instructions.
```

---

# PHASE 2 — CODEX

## Goal

Codex should behave as:

```text
QA Engineer
Test Engineer
Bug Hunter
Refactoring Engineer
Security Reviewer
```

Codex should not redesign the project unless a genuine defect requires it.

---

# 24. Codex — First Prompt

Run Codex from repository root.

```text
You are the senior QA and reliability engineer for DataSentinel.

Claude Code has built the MVP.

Your job is NOT to redesign the product.

Your job is to inspect the entire repository and make it reliable.

First:
- read README
- inspect architecture
- inspect backend
- inspect frontend
- inspect scripts
- inspect tests
- run the project where possible

Then produce a short test plan covering:

1. unit tests
2. integration tests
3. API tests
4. pipeline regression tests
5. incident-injection tests
6. anomaly-detection tests
7. RCA evidence tests
8. validation workflow tests
9. error-path tests

After the plan, implement the missing high-value tests.

Prioritise the end-to-end FILTER REGRESSION workflow.

Important:
- do not change behaviour merely to make tests pass
- fix actual defects
- preserve architecture unless clearly broken
- avoid unnecessary dependencies
- use deterministic fixtures
- mock external LLM calls
- never require real API keys in automated tests

Run the tests and keep fixing failures until the important suite passes.
```

---

# 25. Codex Test Requirements

Codex should add tests for:

## Data Generator

```text
same seed → same output
required columns present
valid countries generated
no invalid negative revenue
```

---

## Data Profiler

```text
correct row count
correct null percentage
correct duplicates
correct schema
```

---

## Filter Incident

Before incident:

```text
UK present
Germany present
Italy present
```

After incident:

```text
UK present
Germany missing
Italy missing
row count sharply reduced
```

---

## Detection

Expected:

```text
severity = CRITICAL
row_count anomaly exists
categorical disappearance detected
```

---

## Git Evidence

Verify:

```text
changed file identified
country-filter line identified
diff available
```

---

## RCA

Mock LLM.

Ensure the evidence request contains:

```text
anomalies
Git diff
pipeline metadata
```

Ensure malformed LLM output fails safely.

---

## Validation

After correct patch:

```text
countries restored
row count within expected tolerance
incident resolved
```

---

# 26. Codex — Security and Robustness Prompt

```text
Now perform a security and robustness review of DataSentinel.

Focus specifically on:

- subprocess execution
- Git command handling
- path traversal
- arbitrary file modification
- unsafe patch application
- API input validation
- accidental API-key leakage
- prompt injection from repository content
- malformed LLM responses
- frontend error handling
- CORS
- oversized request inputs
- exception handling

For every issue:

1. explain the risk briefly
2. fix it if feasible
3. add a test where useful

Do not add enterprise complexity that is unnecessary for a hackathon.
```

---

# 27. Codex — Refactor Prompt

```text
Perform a final maintainability pass on DataSentinel.

Look for:

- duplicated code
- giant functions
- unclear naming
- missing type hints
- dead code
- hidden coupling
- brittle file paths
- inconsistent error models
- duplicated constants
- configuration that should be centralised

Refactor only when it improves reliability or clarity.

Run all tests afterward.

Do not alter working UX or the main hackathon demo unnecessarily.
```

---

# 28. Codex Acceptance Criteria

Before moving to IBM Bob:

```text
[ ] backend starts cleanly
[ ] frontend starts cleanly
[ ] no real API key needed for tests
[ ] critical tests pass
[ ] filter regression demo works
[ ] reset demo works
[ ] malformed incident requests handled
[ ] Git analyser is safe
[ ] patch workflow guarded
[ ] README instructions are accurate
```

Commit:

```bash
git add .
git commit -m "test: harden DataSentinel MVP"
```

---

# PHASE 3 — IBM BOB 2.0

## Goal

IBM Bob is not being used merely as another code generator.

Bob should demonstrate:

- repository understanding
- planning
- multi-agent/subagent workflows
- implementation
- independent review
- testing
- improvement of a real existing project

This becomes part of the hackathon story.

---

# 29. Import DataSentinel Into IBM Bob

Open the completed repository in IBM Bob.

Run Bob's project initialisation flow.

If supported in the current environment:

```text
/init
```

The goal is to create or improve repository-level context such as:

```text
AGENTS.md
Bob-specific project guidance
repository conventions
```

---

# 30. AGENTS.md Suggested Content

Bob may generate this itself, but DataSentinel should communicate:

```text
PROJECT:
DataSentinel — Autonomous Data Reliability Engineer

MISSION:
Detect silent data-pipeline failures, investigate evidence, identify likely root causes, propose safe remediation, and validate recovery.

CRITICAL DEMO:
Filter regression causes Germany and Italy data to disappear while the pipeline technically succeeds.

KEY DESIGN PRINCIPLES:
1. deterministic detection before LLM reasoning
2. evidence-grounded RCA
3. safe remediation
4. reproducible demo
5. clear separation between detection, investigation, remediation, and validation
6. no secrets in repository
7. automated tests must not require external LLM APIs
8. filter-regression workflow must remain stable

TECH STACK:
FastAPI
Python
pandas
pytest
Next.js
React
TypeScript
Tailwind

IMPORTANT DIRECTORIES:
backend/app/pipeline
backend/app/profiling
backend/app/detection
backend/app/investigation
backend/app/remediation
backend/app/validation
frontend
tests

DO NOT:
- add Kubernetes
- introduce microservices
- introduce unnecessary databases
- replace deterministic checks with LLM calls
- auto-apply unsafe patches
```

---

# 31. IBM Bob — Plan Mode Prompt

Use Bob's planning capability first.

```text
Analyze the complete DataSentinel repository.

Do not modify code yet.

DataSentinel is an Autonomous Data Reliability Engineer that detects silent pipeline failures and performs evidence-grounded root-cause analysis.

I want you to assess this repository as if it were going toward a production pilot.

Investigate:

1. pipeline architecture
2. anomaly detection
3. data profiling
4. incident lifecycle
5. Git investigation
6. RCA evidence grounding
7. patch/remediation safety
8. validation workflow
9. automated testing
10. frontend/backend integration
11. observability
12. maintainability

Identify the highest-value improvements that can realistically be completed during a hackathon.

Rank recommendations using:

- user impact
- reliability impact
- demo impact
- implementation complexity

Do not propose broad rewrites.

Return a focused implementation plan.
```

---

# 32. Bob Subagent Strategy

Use specialised subagents where available.

Suggested responsibilities:

```text
                    IBM BOB
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
Pipeline Agent    Reliability Agent   Security Agent

       │               │                │
       ▼               ▼                ▼
pipeline flow     detection logic     patch safety
profiles          validation          subprocess
incident paths    test gaps           API security

       └───────────────┼────────────────┘
                       │
                       ▼
                  Main Bob
                       │
                       ▼
                Improvement Plan
```

---

# 33. Bob Repository Analysis Prompt

```text
Use focused repository-analysis subagents.

Subagent 1:
Inspect the pipeline, profiling, and anomaly-detection code.
Find logic gaps that could create false positives, false negatives, or inconsistent incident severity.

Subagent 2:
Inspect incident investigation, evidence building, Git analysis, and RCA.
Check whether every RCA conclusion is actually grounded in concrete evidence.

Subagent 3:
Inspect remediation and validation.
Focus on unsafe patch application, incomplete rollback handling, and situations where an incident could be marked resolved incorrectly.

Subagent 4:
Inspect the automated tests.
Find the most important untested behaviour.

Subagent 5:
Inspect the frontend/backend integration and demo path.
Find anything that could fail during a live hackathon presentation.

Return each subagent's findings independently.
Then synthesise them into one prioritised improvement plan.
Do not change code yet.
```

---

# 34. Bob Agent Mode — Implementation Prompt

After selecting the best improvements:

```text
Implement the approved DataSentinel reliability improvements.

Constraints:

- preserve current architecture
- preserve the polished filter-regression demo
- prefer small targeted changes
- add tests for each important behavioural change
- do not introduce unnecessary infrastructure
- do not require real LLM API calls during automated tests
- keep RCA evidence-grounded
- keep remediation safe

For each completed change:

1. explain what changed
2. explain why
3. identify affected files
4. run relevant tests

Continue until the selected improvements are implemented and verified.
```

---

# 35. Bob Actor-Critic Workflow

A strong hackathon demonstration is to make Bob implement and independently critique a change.

Example target:

**Safer incident remediation**

Actor task:

```text
Implement a safer patch-application workflow for DataSentinel.

Requirements:

- patch preview required
- only allowed repository files may be modified
- create backup or reversible state
- reject malformed patches
- rerun targeted tests
- rollback on failed validation
- incident can only be marked resolved after validation succeeds

Add automated tests.
```

Critic task:

```text
Act as an independent critic.

Review the new DataSentinel remediation workflow.

Do not assume the implementation is correct.

Try to find:
- unsafe file writes
- rollback failures
- validation bypasses
- false resolution states
- untested error conditions

Return concrete findings referencing files and code paths.

Do not modify code.
```

Then ask Bob:

```text
Reconcile the actor implementation with the critic findings.

Fix valid issues.

Reject incorrect criticism with evidence.

Run the complete relevant test suite afterward.
```

This is excellent material for the final demo.

---

# 36. IBM Bob — Final Validation Prompt

```text
Perform final release validation for DataSentinel.

Do not add new features.

Verify:

1. clean installation instructions
2. backend startup
3. frontend startup
4. synthetic-data generation
5. healthy pipeline
6. filter-regression injection
7. anomaly detection
8. incident creation
9. Git investigation
10. RCA
11. patch generation
12. safe patch application
13. pipeline rerun
14. validation
15. incident resolution
16. incident report generation
17. automated tests
18. demo reset

Fix blockers only.

Produce a concise release-readiness report at the end.
```

---

# 37. Final Demo Flow

The live demo must be rehearsed.

## Step 1

Show healthy dashboard.

```text
Pipeline Status: SUCCESS
Data Health: HEALTHY
```

---

## Step 2

Click:

```text
Inject Incident
→ Filter Regression
```

---

## Step 3

Run pipeline.

Show:

```text
Pipeline Status: SUCCESS
```

Pause.

Then say:

> The pipeline succeeded, but the data is wrong.

---

## Step 4

DataSentinel detects:

```text
CRITICAL INCIDENT

Rows: -66%
Germany: disappeared
Italy: disappeared
```

---

## Step 5

Click:

```text
Investigate
```

Display:

```text
Data evidence
Git evidence
Source file
Changed line
Likely root cause
Confidence
```

---

## Step 6

Show diff:

```diff
- country.isin(["UK", "Germany", "Italy"])
+ country == "UK"
```

---

## Step 7

Click:

```text
Generate Fix
```

---

## Step 8

Apply safely.

---

## Step 9

Validate.

Show:

```text
✓ pipeline rerun
✓ countries restored
✓ row count restored
✓ tests passed
✓ incident resolved
```

---

# 38. Bob Story During Presentation

After demonstrating DataSentinel itself, briefly explain development workflow:

```text
We initially built the vertical slice using Claude Code.

We used Codex as an independent testing and reliability engineer.

Then we moved the working repository into IBM Bob.

Bob analysed the entire codebase rather than starting from a blank prompt.

Using Bob's planning and agentic workflow, we identified reliability gaps.

Specialised analyses reviewed:
- pipeline logic
- incident detection
- RCA grounding
- remediation safety
- testing
- demo resilience

Bob then implemented selected improvements.

We also used an actor-critic workflow:
one agent implemented safer remediation,
another independently attacked the implementation,
and Bob reconciled the results.

The final system was validated again before release.
```

---

# 39. Important Hackathon Rule for Our Workflow

Claude Code and Codex are development accelerators.

IBM Bob must have **visible, demonstrable ownership of meaningful engineering work** in the final repository.

Good examples:

```text
Bob designed the final reliability improvement plan.
Bob identified a validation weakness.
Bob implemented safe remediation.
Bob added missing regression tests.
Bob ran an independent critic.
Bob fixed critic findings.
Bob produced final release validation.
```

Weak example:

```text
Bob changed README formatting.
```

Avoid that.

---

# 40. Division of Responsibility

| Tool | Primary Role |
|---|---|
| Claude Code | Lead MVP builder |
| Codex | QA, tests, robustness, refactoring |
| IBM Bob | Repository intelligence, planning, subagents, engineering improvements, independent validation |
| Human | Product decisions, architecture approval, demo control, final judgement |

---

# 41. Definition of Done

## Product

```text
[ ] healthy pipeline works
[ ] filter incident works
[ ] pipeline still reports success
[ ] anomaly detected
[ ] severity assigned
[ ] Git evidence collected
[ ] root cause identified
[ ] confidence shown
[ ] patch generated
[ ] patch safely applied
[ ] pipeline rerun
[ ] validation succeeds
[ ] incident resolved
[ ] report generated
```

## Engineering

```text
[ ] FastAPI modular
[ ] frontend stable
[ ] configuration centralised
[ ] no secrets committed
[ ] deterministic tests
[ ] external LLM mocked in tests
[ ] Git subprocess safe
[ ] patch application guarded
[ ] README accurate
```

## Hackathon

```text
[ ] IBM Bob used meaningfully
[ ] Bob planning demonstrated
[ ] Bob repository understanding demonstrated
[ ] Bob agent/subagent workflow demonstrated
[ ] Bob implementation visible in Git history
[ ] Bob validation demonstrated
[ ] demo takes less than 5 minutes
```

---

# 42. Git Strategy

Recommended branches:

```text
main
claude-mvp
codex-hardening
bob-improvements
```

Suggested workflow:

```bash
git checkout -b claude-mvp
```

Claude work.

Then:

```bash
git checkout -b codex-hardening
```

Codex work.

Then:

```bash
git checkout -b bob-improvements
```

Bob work.

This makes contribution history visible.

---

# 43. Suggested Commit History

```text
feat: initialise DataSentinel architecture

feat: add synthetic data pipeline

feat: add pipeline profiling and anomaly detection

feat: add incident injection workflow

feat: add Git-based root cause investigation

feat: add remediation and validation workflow

feat: add DataSentinel dashboard

test: add pipeline and anomaly unit tests

test: add end-to-end filter regression tests

fix: harden Git and patch execution

refactor: improve incident state handling

bob: improve evidence-grounded RCA

bob: add safe remediation rollback

bob: add independent validation coverage

bob: final release hardening
```

---

# 44. Demo Safety

Before presenting:

```text
1. reset demo
2. run healthy pipeline
3. verify dashboard
4. inject incident
5. run pipeline
6. test investigate button
7. test patch generation
8. test validation
9. restart backend
10. restart frontend
11. repeat demo twice
```

Have a pre-generated incident available in case an external LLM API fails.

DataSentinel should still be able to show:

- statistical anomaly detection
- collected Git evidence
- deterministic demo workflow

without an external model.

---

# 45. Stretch Goals

Only implement after core demo is stable.

Possible extensions:

- PySpark backend
- DuckDB support
- Great Expectations integration
- Evidently integration
- Airflow connector
- Databricks connector
- Slack incident notifications
- GitHub PR generation
- MCP integration
- vector search over previous incidents
- incident memory
- root-cause ranking
- rollback automation
- multiple pipeline support
- data contracts

---

# 46. Things We Should NOT Build

Do not waste hackathon time on:

```text
Kubernetes
Kafka
full authentication system
multi-tenant billing
complex RBAC
enterprise database
distributed agents
model fine-tuning
custom ML training
production Databricks deployment
full Airflow deployment
full Azure infrastructure
```

They do not improve the core demo enough.

---

# 47. Elevator Pitch

> Data pipelines can succeed while the data silently fails. DataSentinel acts as an autonomous data reliability engineer: it detects abnormal data behaviour, investigates pipeline and Git evidence, identifies the likely root cause, proposes a safe fix, reruns validation, and documents the incident.

---

# 48. 30-Second Demo Pitch

> This pipeline says SUCCESS, but we've just lost two-thirds of our customer data. Traditional orchestration sees a successful job. DataSentinel sees a data incident. It detects the distribution change, traces it to a code change in the country filter, explains the impact, generates a patch, validates the repair, and only then marks the incident resolved.

---

# 49. Key Differentiator

DataSentinel is not:

```text
another chatbot
another generic code-review agent
another dashboard
```

It combines:

```text
Data Reliability
+
Software Repository Intelligence
+
Root Cause Analysis
+
Safe Remediation
+
Agentic Development
```

---

# 50. Start Here

Create the repository.

```bash
mkdir datasentinel
cd datasentinel
git init
```

Save this document as:

```text
DATASENTINEL_BUILD_PLAN.md
```

Then start:

```text
PHASE 1 → Claude Code
PHASE 2 → Codex
PHASE 3 → IBM Bob
```

The first target is not the complete platform.

The first target is:

```text
HEALTHY PIPELINE
      ↓
FILTER BUG
      ↓
SUCCESSFUL BUT BAD PIPELINE
      ↓
ANOMALY DETECTION
      ↓
ROOT CAUSE
      ↓
FIX
      ↓
VALIDATION
```

Once this vertical slice works, everything else is secondary.

---

# DataSentinel

**Autonomous Data Reliability Engineer**

> Your pipeline can succeed while your data fails.


---

# 51. Hackathon Submission Strategy

The implementation plan above remains valid. The following requirements should now be treated as **release requirements**, not optional polish.

## Submission Deliverables

Before final submission, DataSentinel should have:

```text
[ ] Public GitHub repository
[ ] Working deployed application URL
[ ] Strong README
[ ] Project cover image
[ ] Short project description
[ ] Detailed project description
[ ] Demo/pitch video kept within the hackathon platform's stated limit
[ ] PDF pitch deck
[ ] Architecture diagram
[ ] Clear IBM Bob usage evidence
[ ] Business-value explanation
[ ] Future roadmap
```

Do not rely on a local-only demo.

The live deployment should expose the golden-path workflow:

```text
HEALTHY PIPELINE
      ↓
INJECT INCIDENT
      ↓
PIPELINE STILL SAYS SUCCESS
      ↓
DATASENTINEL DETECTS BAD DATA
      ↓
INVESTIGATE
      ↓
ROOT CAUSE
      ↓
PROPOSED FIX
      ↓
VALIDATE
      ↓
RESOLVED
```

---

# 52. Judging Optimization

The final product and presentation should explicitly demonstrate four areas.

## A. Application of Technology

IBM Bob must perform meaningful engineering work on the final repository.

Strong evidence includes:

```text
Bob repository analysis
Bob Plan mode
Bob subagent investigations
Bob implementation commits
Bob-generated/fixed tests
Bob actor-critic review
Bob final release validation
```

Avoid making Bob look like a final documentation tool.

Claude Code and Codex can accelerate development, but the final story should clearly show why IBM Bob materially improved DataSentinel.

---

## B. Presentation

The presentation should prioritize the working product over architecture slides.

Recommended sequence:

```text
1. Problem
2. Healthy pipeline
3. Inject silent data failure
4. Pipeline still reports SUCCESS
5. DataSentinel detects the incident
6. Root-cause investigation
7. Proposed remediation
8. Validation and recovery
9. IBM Bob contribution
10. Business value and roadmap
```

Opening line:

> A data pipeline can succeed while its data fails.

Closing line:

> DataSentinel — because successful pipelines can still produce failed data.

---

## C. Business Value

Primary target user:

```text
Data Engineers
Analytics Engineers
Data Platform Teams
ML Engineers
Data Reliability / Data SRE Teams
```

Primary buyer:

```text
Companies operating production data pipelines on:
Databricks
Snowflake
dbt
Airflow
Azure Data Factory
similar data platforms
```

The problem is not simply failed jobs.

The problem is:

```text
PIPELINE STATUS = SUCCESS
DATA QUALITY = FAILED
```

DataSentinel reduces manual investigation across:

```text
logs
schemas
Git changes
data profiles
pipeline runs
validation rules
```

Possible future SaaS positioning:

```text
Developer
Team
Enterprise
```

Billing does not need to be implemented during the hackathon.

---

## D. Originality

The project should NOT be positioned as:

```text
generic AI debugger
generic coding agent
generic code reviewer
generic chatbot for logs
```

The differentiator is:

> DataSentinel correlates **data-state anomalies** with **pipeline execution evidence** and **repository/code changes** to diagnose silent data failures.

Core originality story:

```text
               PIPELINE SAYS SUCCESS
                        │
                        ▼
              Is the data actually healthy?
                        │
                        ▼
                  DataSentinel
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
     Data State      Run State       Code State
        │               │               │
   profiles/drift     logs/meta      Git/change
        └───────────────┼───────────────┘
                        ▼
                 Evidence-grounded RCA
                        │
                        ▼
                   Safe remediation
                        │
                        ▼
                     Validation
```

---

# 53. Bob Evidence Checklist

Capture proof while working with IBM Bob.

Save screenshots or recordings of:

```text
[ ] Bob opening/understanding the repository
[ ] Bob planning improvements
[ ] Bob subagent outputs
[ ] Bob identifying a real defect or reliability gap
[ ] Bob implementing an improvement
[ ] Bob running tests
[ ] Bob critic/reviewer findings
[ ] Bob fixing valid critic findings
[ ] Bob final validation result
```

Also preserve Git commits from the Bob phase.

Recommended commit prefix:

```text
bob:
```

Examples:

```text
bob: improve evidence-grounded RCA
bob: add safe remediation rollback
bob: prevent false incident resolution
bob: add final validation coverage
```

This gives judges visible evidence that Bob contributed to the finished system.

---

# 54. Deployment Requirement

Deployment is part of the MVP definition of done.

Suggested deployment:

```text
Frontend:
Vercel

Backend:
Render / Railway / Fly.io or equivalent

Demo state:
local JSON/files or lightweight persistent storage
```

Deployment goals:

```text
[ ] no secrets committed
[ ] environment variables configured
[ ] reset-demo endpoint works
[ ] demo does not depend on developer laptop
[ ] external LLM outage has graceful fallback
[ ] app can show a deterministic pre-generated incident if necessary
```

The golden-path demo must remain usable even if an external model API is unavailable.

---

# 55. Pitch Assets To Prepare

After the MVP is stable, create:

```text
1. Cover image
2. Architecture diagram
3. 5–7 slide pitch deck
4. Short description
5. Long submission description
6. Demo video
7. README screenshots/GIF
```

Suggested pitch deck:

```text
Slide 1 — DataSentinel
Slide 2 — The silent data failure problem
Slide 3 — How DataSentinel works
Slide 4 — Live incident / RCA workflow
Slide 5 — IBM Bob contribution
Slide 6 — Business value
Slide 7 — Roadmap
```

---

# 56. Final Priority Order

Do not optimize for every feature equally.

Priority order:

```text
P0 — WORKING FILTER-REGRESSION GOLDEN PATH
P0 — STABLE DEPLOYMENT
P0 — MEANINGFUL IBM BOB CONTRIBUTION

P1 — STRONG VISUAL DASHBOARD
P1 — TEST COVERAGE
P1 — SAFE REMEDIATION
P1 — CLEAR BUSINESS STORY

P2 — EXTRA INCIDENT TYPES
P2 — EXTRA CONNECTORS
P2 — ADVANCED DRIFT METHODS
P2 — ADDITIONAL AGENT FEATURES
```

If time becomes limited, remove P2 features before compromising the P0 demo.

---

# 57. Updated Definition of Done

The hackathon version is complete only when all three layers are ready.

## Product

```text
[ ] working golden-path incident
[ ] deterministic anomaly detection
[ ] evidence-grounded RCA
[ ] safe fix workflow
[ ] post-fix validation
[ ] polished UI
```

## IBM Bob

```text
[ ] repository analysed by Bob
[ ] Bob plan captured
[ ] Bob subagent work captured
[ ] Bob implemented meaningful changes
[ ] Bob reviewed/validated those changes
[ ] Bob commits visible
```

## Submission

```text
[ ] deployed URL
[ ] public repository
[ ] README
[ ] cover image
[ ] pitch deck PDF
[ ] video
[ ] project description
[ ] architecture visual
[ ] business-value story
```

