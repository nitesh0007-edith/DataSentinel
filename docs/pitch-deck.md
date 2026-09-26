# DataSentinel — Seven-Slide Pitch

Use a 16:9 layout with short text, large numbers and real screenshots. Public demo: https://datasentinel-seven.vercel.app. This document is slide content; no PDF deck has been exported.

## Slide 1 — DataSentinel

**Exact on-slide text**

> DataSentinel<br>
> Your pipeline can succeed while your data fails.<br>
> SUCCESS / CRITICAL

**Visual recommendation:** Crop the two status tiles from `screenshots/critical.png`; green execution, red data health. Add the public demo URL in a small footer.

**Speaker notes:** “This pipeline finished successfully. Its output still lost two entire markets. DataSentinel investigates that gap and validates an approved repair.”

## Slide 2 — The Silent Failure Problem

**Exact on-slide text**

> Pipeline: SUCCESS<br>
> Data: CRITICAL<br>
> Bad filter · Schema drift · Null explosion · Duplicate ingestion

**Visual recommendation:** Two contrasting status cards with four small text labels underneath.

**Speaker notes:** “A job can run without an exception and still produce incorrect data. Execution monitoring tells us the job ran. We also need to check what it produced and connect that result to the code that changed.”

## Slide 3 — How DataSentinel Works

**Exact on-slide text**

> DETECT → INVESTIGATE → ROOT CAUSE → FIX → VALIDATE → REPORT<br>
> DATA + RUN + CODE<br>
> Human approval before apply

**Visual recommendation:** Use the central workflow from [architecture.svg](architecture.svg). Keep the approval boundary visible; omit small module text if projecting.

**Speaker notes:** “Profiles and rules establish the anomaly. Run history and real Git evidence help identify the cause. The operator previews and approves the patch. DataSentinel reruns and tests the pipeline before resolving the incident.”

## Slide 4 — Live Evidence

**Exact on-slide text**

> 110,000 → 43,760 rows<br>
> −60.2%<br>
> Germany: 0 · Italy: 0<br>
> pipelines/customer_transform.py:46<br>
> Real Git commit. Real diff.

**Visual recommendation:** Pair the critical country chart with the offending diff from `screenshots/git-evidence.png`. Use the actual session commit shown in the image; hashes vary after reset.

**Speaker notes:** “The filter changed from UK, Germany and Italy to UK only. The pipeline still reports SUCCESS. The observed loss is 66,240 rows. Investigation points to line 46 and the actual transformation commit. The confidence shown is a heuristic score, not a calibrated probability.”

## Slide 5 — IBM Bob

**Exact on-slide text**

> Working repository<br>
> ↓ Bob repository analysis<br>
> ↓ Missing recovery path identified<br>
> ↓ Operator rollback<br>
> ↓ RCA hardening<br>
> ↓ Regression + adversarial tests<br>
> ↓ Independent critic<br>
> RELEASE READY

**Visual recommendation:** A compact vertical journey. Highlight the recovery gap and rollback. Small footer: “Initial MVP: Claude Code · QA/deployment/release: Codex”.

**Speaker notes:** “Bob worked on an existing MVP. Its independent assessment found that a committed repair could fail validation without a safe recovery path. Bob implemented operator-controlled rollback, strengthened evidence trust boundaries and persistence/idempotency, added tests and performed an independent critic review. The supplied assessment reported no HIGH/CRITICAL blockers and RELEASE READY: YES. Bob did not build the whole product.”

## Slide 6 — Business Value

**Exact on-slide text**

> Logs · Schemas · Tables · Git · Pipeline history<br>
> ↓<br>
> One evidence-grounded workflow<br>
> For data and platform engineering teams

**Visual recommendation:** Five signals converge into a single incident view. Use the root-cause screenshot as the outcome.

**Speaker notes:** “Data Engineers, Analytics Engineers, platform teams and ML Engineers often investigate across all these sources. DataSentinel brings them into a single investigation and recovery workflow. We have not measured customer time savings or revenue impact; the live MVP demonstrates the mechanism.”

## Slide 7 — What’s Next

**Exact on-slide text**

> Databricks · Airflow · dbt · Snowflake · ADF<br>
> GitHub · Slack · Incident memory<br>
> Successful pipeline ≠ healthy data.

**Visual recommendation:** A simple connector map with the resolved screenshot as the closing image. Label these connectors “planned”. Public demo URL at the bottom.

**Speaker notes:** “The current demo uses a generated monitored Git repository and synthetic data. Next come production connectors, historical incident memory and enterprise isolation. Successful pipeline doesn’t always mean healthy data. That’s what DataSentinel is built to catch.”
