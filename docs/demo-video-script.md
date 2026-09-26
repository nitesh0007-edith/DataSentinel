# DataSentinel Demo Video — 4:30

Target runtime: **4 minutes 30 seconds**, always below five minutes. Record the real frontend at https://datasentinel-seven.vercel.app with heuristic RCA. Rehearse once, reserve the shared demo during recording, and trim waits rather than rushing the narration. No secret settings or backend URLs belong on screen.

The ordinary hosted golden path resolves correctly. For the safety segment, use the architecture recovery diagram unless a genuine failed committed fix is available. Never present the local fixture as a hosted incident.

## 0:00–0:20 — Hook

**Narration:** “A pipeline can succeed while its data fails. Here, the job is green, but the data is critical. Two entire markets have disappeared. DataSentinel connects the data, the run and the code to find out what happened.”

**Screen action:** Open on the captured critical hero, then reveal the country chart.

**Visible:** SUCCESS / CRITICAL, 43,760 rows, Germany and Italy missing.

**Transition:** “Here’s why execution status alone misses this.”

## 0:20–0:45 — Problem

**Narration:** “An orchestrator can tell us whether a job ran. A bad filter can still execute perfectly. So can a renamed column, duplicated batch or transformation that fills values with nulls. The investigation usually spans tables, profiles, logs, pipeline history and Git. We need those signals together.”

**Screen action:** Show the problem slide, then switch to the live dashboard.

**Visible:** Execution versus data-health contrast and the four example failures.

**Transition:** “Let’s reproduce one.”

## 0:45–2:20 — Live Demo

**Narration and screen actions:**

| Time | Narration | Screen action / visible evidence |
|---|---|---|
| 0:45–1:00 | “Reset gives us a reproducible pipeline and synthetic customers. The healthy baseline has 110,000 rows across the UK, Germany and Italy.” | Reset Demo → Run Healthy Pipeline. Show SUCCESS / HEALTHY and baseline countries. |
| 1:00–1:15 | “Now a developer narrows the country filter to UK only. The pipeline succeeds, but only 43,760 rows remain.” | Select Filter regression → Inject Incident → Run Pipeline. Execution SUCCESS; data is not checked until Detect. |
| 1:15–1:30 | “Detection catches a 60.2 percent drop. Germany and Italy have disappeared, and the country distribution has shifted.” | Detect. Show CRITICAL, −60.2%, missing countries. |
| 1:30–1:50 | “Investigation connects these observations to the real monitored Git history. It identifies customer_transform.py, line 46, and shows the actual change from three markets to one.” | Investigate. Scroll through Root cause and Offending change. Show file, line, heuristic confidence and real diff. |
| 1:50–2:05 | “The reverse patch is a proposal. I review it and explicitly approve the apply step. DataSentinel checks the source hash and commits the repair.” | Generate Fix → show proposed diff → Apply Fix. |
| 2:05–2:20 | “Validation reruns the pipeline, compares the data and runs repository tests. The countries and all 110,000 rows are back. Only then is the incident resolved.” | Validate. Show passed checks and RESOLVED / HEALTHY. |

**Transition:** “The recovery path is where IBM Bob made a specific contribution.”

## 2:20–3:15 — IBM Bob Story

**Narration:** “The working repository already existed. Claude Code built the initial MVP, and Codex handled QA and hardening. IBM Bob initialized and understood the repository, then independently assessed its reliability. Bob found a gap: if a committed repair failed validation, the operator had no safe recovery path. Bob implemented operator-controlled rollback, including the dashboard controls. It also hardened the boundary between model explanations and evidence, improved persistence ordering and duplicate-apply behavior, and added regression and adversarial tests. An independent Bob critic reviewed the changes. The supplied review reported no high or critical blockers and release ready. Bob improved the repository’s reliability; it didn’t build the entire product.”

**Screen action:** Show the seven-step Bob journey from slide 5, with the recovery gap highlighted.

**Visible:** Existing repository → assessment → missing recovery path → rollback → RCA hardening → tests → independent critic.

**Transition:** “Here’s what that recovery means.”

## 3:15–3:45 — Rollback Safety

**Narration:** “If validation fails after a committed fix, the incident stays open. The operator can choose rollback. That restores the pre-fix source as a new commit and preserves the failure evidence. It returns the incident to a retryable state. Rollback is recovery of the repository, not a claim that the data is healthy. A new approved fix still has to pass validation.”

**Screen action:** Show the labeled architecture path **VALIDATION_FAILED → operator ROLLBACK → retryable**. Use an actual hosted failure only if one exists; otherwise keep this segment explicitly a workflow diagram.

**Visible:** Operator approval, restore commit, retry and validation before resolution.

**Transition:** “That keeps the investigation and the repair connected.”

## 3:45–4:10 — Business Value

**Narration:** “This is for data engineering and platform teams, analytics engineers, and teams feeding machine-learning systems. Instead of stitching together data, schemas, run history and Git, they get one evidence-grounded workflow. This MVP uses synthetic data. The next step is connecting it to platforms such as Databricks, Airflow, dbt and Snowflake.”

**Screen action:** Show slide 6, then the planned connector map.

**Visible:** Signals converging into one workflow; integrations marked planned.

**Transition:** Return to the resolved dashboard.

## 4:10–4:30 — Close

**Narration:** “Successful pipeline doesn’t always mean healthy data. That’s what DataSentinel is built to catch. It detects the failure, investigates real evidence and validates a repair that the operator approves. You can try the live demo at the link on screen.”

**Screen action:** Finish on healthy data and the public frontend URL.

**Visible:** RESOLVED, SUCCESS / HEALTHY, https://datasentinel-seven.vercel.app.

**Transition:** Fade out before 4:30.

## Recording Checklist

- Keep the same browser size and avoid browser chrome, private tabs and notifications.
- Rehearse API waits; use honest cuts between operations without replacing results.
- Make the diff and country chart readable. Avoid scrolling while speaking key numbers.
- Attribute Bob’s critic result to the supplied assessment.
- Export, add captions and confirm the final runtime is under five minutes.

This is a storyboard and narration script; no final video has been recorded.
