# Release Validation — 26 September 2026

## Engineering and Hosted Checks

The verified engineering release passed **62/62 backend tests**, frontend TypeScript checking (`npm run lint`), a production frontend build and the golden-path script. These results precede this content-only pass; the full suite was not rerun because application logic was not changed.

The public frontend is https://datasentinel-seven.vercel.app. Hosted health, exact-origin CORS, reset, detection, investigation, approved remediation and resolution were verified. State fetched before and after the owner-performed Render restart was byte-identical, retaining runs, incident history and resolved state.

## Verified P0 Evidence

| Observation | Result |
|---|---|
| Healthy output | 110,000 rows |
| Countries | UK 43,760; Germany 38,710; Italy 27,530 |
| Regressed output | 43,760 rows; 66,240 lost; −60.2% rounded |
| Execution / detection | SUCCESS / CRITICAL; four anomalies |
| Root cause | `pipelines/customer_transform.py:46`; real session commit |
| Confidence | 95% heuristic score, not calibrated probability |
| Correct repair | 110,000 rows, all countries restored, RESOLVED |
| Validation | Nine passed checks, including six repository tests |

## Content Capture

The repeatable release script drives the **deployed dashboard's normal controls**, uses heuristic RCA and a 1440 × 1000 viewport, then leaves the hosted demo resolved. Seven real hosted images and their provenance are under `screenshots/`. No HTML mock, model key or failure injection is used.

Correct remediation does not produce live failed-validation or rollback stages. Two older local recovery examples remain isolated under `screenshots/local-fixture/`, explicitly labeled with their original fixture provenance. The README uses hosted images only; the video storyboard uses a labeled recovery diagram.

Bob's critic result—no HIGH/CRITICAL blockers and RELEASE READY: YES—is attributed to the supplied project assessment. This content pass does not rerun Bob's critic.

## Final Content Checks

Script syntax, local Markdown targets, image dimensions/provenance, SVG XML/rendering, public-link consistency and `git diff --check` are checked during this content pass. No application logic or deployment configuration was changed. Nothing is committed or deployed by this task.

## Remaining Owner Work

Record/export the video under five minutes, export the seven-slide deck, and fill the submission form. A GIF/MP4 micro demo is optional. Live recovery screenshots require a genuine failed committed repair; none is manufactured for this release. Review and commit the content branch when satisfied.
