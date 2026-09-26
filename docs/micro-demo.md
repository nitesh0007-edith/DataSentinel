# README Micro Demo — 30 Seconds

Record https://datasentinel-seven.vercel.app at 1440 × 1000, using heuristic RCA and the real dashboard. Reserve the shared demo during recording. Keep only the product window and use cuts to remove waits; do not replace UI values.

| Time | Action | Visible result |
|---|---|---|
| 0–5s | Reset Demo → Run Healthy Pipeline before the opening frame | SUCCESS / HEALTHY, 110,000 rows |
| 5–10s | Select Filter regression → Inject Incident → Run Pipeline | Real regression commit; successful execution |
| 10–15s | Detect | SUCCESS / CRITICAL, 43,760, −60.2%, missing Germany and Italy |
| 15–20s | Investigate; scroll to root cause and Git diff | customer_transform.py:46; three-country filter narrowed to UK |
| 20–25s | Generate Fix; show diff; click Apply Fix | Proposed patch and explicit approval |
| 25–30s | Validate; return to top | RESOLVED / HEALTHY, restored countries and 110,000 rows |

## Lightweight Recording

On macOS, use **Shift–Command–5 → Record Selected Portion**, frame the dashboard, disable microphone if making a silent loop, and record a rehearsed run. Trim waits with an existing editor. Aim for 25–30 seconds and export MP4 for readability. No extra video dependencies are required.

The existing Playwright capture tool produces still images:

```sh
node scripts/capture_release_screenshots.mjs
```

It resets the shared demo and leaves it resolved. It does not produce a GIF or edited video. Add the recording to the README only after checking its actual results and public hosting link.
