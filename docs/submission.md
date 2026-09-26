# Hackathon Submission

## Project Title

DataSentinel

## Tagline

Your pipeline can succeed while your data fails.

## Short Description

DataSentinel catches silent data failures in successful pipelines, connects data profiles with real Git evidence, proposes a human-approved repair and validates recovery—with operator-controlled rollback when a committed fix fails.

## Long Description

A green pipeline can still deliver wrong data. A small filter change can remove entire markets without raising an execution error. Engineers then have to connect tables, profiles, run history and code changes by hand.

DataSentinel is an Autonomous Data Reliability Engineer that connects those signals in one workflow. Deterministic checks compare output against a healthy baseline. Investigation packages data and run evidence alongside real Git history, then heuristic RCA identifies a likely file, line and commit. Optional model explanations are grounded to that evidence; models never calculate anomaly metrics.

In the live synthetic-data demo, a filter regression reduces 110,000 customer rows to 43,760 while the pipeline reports SUCCESS. Germany and Italy disappear. DataSentinel detects CRITICAL data health, identifies `pipelines/customer_transform.py:46` and shows the actual offending Git diff.

Remediation remains under operator control. A proposed reverse patch is previewed, explicitly approved, hash-checked and committed. DataSentinel reruns the pipeline, compares profiles and executes repository tests before marking RESOLVED. If a committed fix fails validation, the operator can roll back, preserve the failure evidence and retry.

IBM Bob independently assessed the existing repository, found the missing committed-fix recovery path, implemented rollback, strengthened RCA trust boundaries and expanded tests. Its independent critic reported no HIGH/CRITICAL blockers and a release-ready assessment. Claude Code built the initial MVP; Codex handled QA, hardening, deployment preparation and release work.

The MVP demonstrates a workflow for data and platform teams investigating silent failures. Planned integrations connect the same approach to production orchestrators and data platforms.

**Live demo:** https://datasentinel-seven.vercel.app

## Problem

Execution success cannot establish data correctness. Narrowed filters, schema drift, null explosions, duplicate batches and distribution shifts may satisfy an orchestrator while breaking analytics or downstream models. Investigation requires correlating evidence across systems.

## Solution

Compare output with a known healthy baseline, investigate data/run/code evidence, propose an approved repair, and validate recovery. Keep failed fixes open and provide an explicit rollback path.

## How It Works

**DETECT → INVESTIGATE → ROOT CAUSE → PROPOSE → APPROVE/APPLY → VALIDATE → REPORT**

1. Profile the data and calculate anomalies deterministically.
2. Combine profiles, run history and real monitored Git changes into an evidence package.
3. Identify a likely root cause, separating observed facts from inference.
4. Preview the patch and wait for human approval; constrain paths and verify hashes before committing.
5. Rerun, re-profile and test. Resolve only on success; allow operator rollback and retry on failed committed remediation.

## How IBM Bob Was Used

**Repository initialization → independent assessment → recovery gap → operator rollback → RCA hardening → test expansion → independent critic → release-ready assessment.**

Bob initialized and understood the already-working repository rather than generating the original product. Its assessment found that a committed fix could fail validation without a safe operator recovery path. Bob implemented source restoration as a new Git commit, preserved failure evidence, returned the incident to a retryable state and added frontend rollback controls.

Bob also hardened the boundary between model explanations and deterministic evidence, improved state/report persistence ordering and duplicate-apply idempotency, documented the single-worker constraint, and added regression and adversarial tests. Its independent critic reported **RELEASE READY: YES**, with **no HIGH/CRITICAL blockers**. This review result is attributed to the project handoff; it is separate from the hosted demo checks.

## Technology Stack

| Area | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI, pandas, Pydantic |
| Testing | pytest, TypeScript checking, production frontend build |
| Infrastructure | Vercel, Render, Git; persistent filesystem state |
| RCA | Deterministic heuristic RCA; optional grounded Anthropic/OpenAI providers |

The public demo uses heuristic RCA without external model keys.

## Key Differentiator

**DATA STATE + RUN STATE + CODE STATE → evidence-grounded root-cause analysis.**

DataSentinel joins the observed output, successful execution and transformation history, then carries the incident through approval, committed remediation, validation and recovery. This combination distinguishes the workflow from chat-only assistance, isolated code review and dashboards that stop at detection.

## Business Value

Primary users are Data Engineers, Analytics Engineers, Data Platform teams, ML Engineers and Data Reliability/Data SRE teams. The workflow brings data profiles, code evidence and recovery checks together, helping teams investigate output that looks operationally successful but is incorrect.

Databricks, Snowflake, dbt, Airflow and Azure Data Factory teams are potential users of future connectors. The MVP uses a generated pipeline repository; these integrations are not yet shipped. No market-size, revenue or measured time-saving claims are made.

## Future Roadmap

Databricks, Airflow, dbt, Snowflake and Azure Data Factory connectors; GitHub evidence correlation; Slack notifications; historical incident memory. Production expansion also requires authentication, tenant isolation and coordinated persistent state.
