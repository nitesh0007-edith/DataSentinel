# Screenshot Capture

## Live Capture

The release images come from **https://datasentinel-seven.vercel.app**, not mocked HTML. The repeatable script uses the existing Playwright development dependency and installed Google Chrome. It uses a 1440 × 1000 viewport, excludes browser chrome and requires the header to show heuristic RCA.

```sh
# Repository root; frontend dependencies must be installed with npm ci
node scripts/capture_release_screenshots.mjs
```

This resets the shared synthetic demo, runs the normal dashboard controls and leaves the hosted incident RESOLVED. Reserve the demo so another visitor does not reset it during capture. No model key is needed. `DEMO_URL` can override the public frontend; `PLAYWRIGHT_CHANNEL` can select an installed browser channel.

[Capture provenance](screenshots/capture.json) records source, time, viewport and stages. The current release contains seven real hosted images.

| Image | Exact action / expected UI |
|---|---|
| `healthy.png` | Reset Demo → Run Healthy Pipeline. SUCCESS / HEALTHY; 110,000 rows. |
| `critical.png` | Select Filter regression → Inject Incident → Run Pipeline → Detect. SUCCESS / CRITICAL; 43,760 rows; −60.2%; Germany and Italy missing. |
| `root-cause.png` | Investigate; scroll Root cause to the top. Source `pipelines/customer_transform.py:46`, confidence score and explanation. |
| `git-evidence.png` | Scroll to Offending change (git show). Actual session commit and three-country-to-UK diff. |
| `proposed-fix.png` | Generate Fix; scroll to Suggested remediation. PROPOSED patch and reverse diff. Applying requires the separate enabled Apply Fix control at the top. |
| `resolved.png` | Apply Fix → Validate; return to top. RESOLVED, SUCCESS / HEALTHY, 110,000 and all countries restored. |
| `validation-passed.png` | Scroll Validation to the top. Passing rerun/profile/test checks. |

## Live Recovery Capture Gap

The ordinary deployed repair is correct and passes validation. No public failure-injection control exists. **No hosted `validation-failed.png` or `rollback.png` is claimed.** Do not change a hosted patch, forge state or install a failure fixture to manufacture these images.

If a genuine committed repair fails validation:

1. Confirm the incident is VALIDATION_FAILED and the patch is APPLIED. Preserve the failure evidence.
2. Capture the top controls with **Roll Back Fix** enabled and the Validation panel showing failed checks, using the same viewport. Save `validation-failed.png` and record the genuine session provenance.
3. Explicitly click **Roll Back Fix**. Capture the activity/restoration commit and patch status ROLLED BACK. The incident returns to ROOT_CAUSE_IDENTIFIED and is retryable. Save `rollback.png`.
4. Generate a new fix, approve apply and validate. Confirm RESOLVED only after all checks pass.

For a presentation without a genuine hosted failure capture, show the recovery path in the [architecture illustration](assets/architecture-doodle.svg). Keep workflow illustrations distinct from live captures.

## Existing Local Recovery Examples

Earlier genuine dashboard images are preserved under `screenshots/local-fixture/`, with their original capture manifest. They use a disclosed local fixture that fails one repository-test check after applying the fix. They are **not deployed screenshots** and are excluded from README live screenshots.

The older local tools are `scripts/screenshot_backend.py` and `scripts/capture_demo_screenshots.mjs --rollback-fixture`; the latter now writes only to `docs/screenshots/local-fixture/` so it cannot overwrite the hosted release images. Read the fixture script before using it; run only against a separate temporary runtime and local frontend. No fixture is part of the deployed application.

### Reproduce the local fixture

These two capture scripts have different purposes: `capture_release_screenshots.mjs` records the hosted golden path; `capture_demo_screenshots.mjs` records a local session, optionally including the disclosed rollback fixture. Both names remain stable for existing commands.

With backend and frontend dependencies installed, use separate terminals:

```sh
# Repository root, backend Python environment active; serves on :8010
python scripts/screenshot_backend.py
```

```sh
# Local frontend pointing only to the fixture backend
cd frontend
NEXT_PUBLIC_API_URL=http://127.0.0.1:8010 npm run dev -- --port 3010
```

```sh
# Repository root; capture the local failure, rollback and retry
DEMO_URL=http://localhost:3010 node scripts/capture_demo_screenshots.mjs --rollback-fixture
```

The fixture uses a temporary runtime, fails one repository-test check, then delegates subsequent checks to the real test runner. Capture commands overwrite their respective images and manifests; do not run them merely to check script syntax or review existing evidence.
