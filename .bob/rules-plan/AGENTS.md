# Project Architecture Rules (Non-Obvious Only)

- The workflow is a linear state machine: reset → baseline → inject → run → detect → investigate → fix → apply → validate → report. All state transitions live in `DataSentinelService` (`app.services.workflow`). Never add state transitions elsewhere.
- Detection is always deterministic (pandas). The LLM only touches the investigation phase (RCA). This boundary is non-negotiable by design principle.
- LLM output is grounded post-hoc (`rca_agent.ground_llm_result`): the LLM's file/commit references are validated against the evidence package before being trusted. Plan accordingly — RCA results will never contain hallucinated paths.
- Persistence is file-only: JSON state file, CSV data files, text patch/profile files. Adding a database is explicitly prohibited.
- All thresholds (row-count change, null rate, categorical drift, etc.) are in `DetectionThresholds` in `config.py`. New detection rules must use these constants, not inline magic numbers.
- The git sandbox (`workspace/pipeline_repo`) is isolated: all commits there use a bot author (`DataSentinel <datasentinel-bot@…>`), and global git hooks/signing are disabled via `-c core.hooksPath=/dev/null` to prevent host config leakage.
- The allowed git commands are hard-coded (`READ_COMMANDS`, `WRITE_COMMANDS` in `git_analyzer.py`). No new subcommands can be added without updating the allowlist.
- Component files are intentionally flat: four frontend component files (`ui.tsx`, `panels.tsx`, `charts.tsx`, `ControlBar.tsx`). Do not propose splitting into subdirectories unless the task specifically requires it.
- `DataSentinelService` holds a `threading.RLock` for concurrency safety. Any new method that mutates state must hold `self._lock`.
- Backend is a single FastAPI process with no background workers or queues. Long operations (reset, run) are synchronous in the API request. Do not introduce async task queues.
