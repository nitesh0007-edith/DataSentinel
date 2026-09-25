"""DataSentinel workflow orchestration.

Owns the demo state machine: reset -> baseline -> inject -> run -> detect ->
investigate -> fix -> apply -> validate -> report. The API layer is a thin shell
over this class, and the scripts/tests drive it directly.
"""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.models import (
    DataHealth,
    DatasetProfile,
    DemoState,
    Incident,
    IncidentStatus,
    IncidentType,
    InvestigationStep,
    PipelineRun,
    RunStatus,
    Severity,
    TimelineEvent,
    utcnow,
)
from app.core.state import StateStore, write_text_atomic
from app.detection.anomaly_engine import detect_anomalies
from app.investigation.evidence_builder import build_evidence
from app.investigation.rca_agent import run_rca
from app.llm.base import LLMProvider
from app.llm.providers import get_llm_provider
from app.pipeline.generator import write_dataset
from app.pipeline.incident_injector import inject_incident, list_scenarios
from app.pipeline.runner import run_pipeline
from app.pipeline.workspace import reset_workspace, workspace_git
from app.profiling.profiler import load_profile, save_profile
from app.remediation.patch_generator import generate_patch
from app.remediation.patch_service import apply_patch
from app.reporting.incident_report import write_report
from app.validation.validator import validate_incident

log = get_logger("workflow")

MAX_EVENTS = 200


class DataSentinelService:
    def __init__(self, settings: Settings, llm_provider: LLMProvider | None = None, use_env_llm: bool = True) -> None:
        self.settings = settings
        settings.ensure_dirs()
        self.store = StateStore(settings.state_path)
        self._lock = threading.RLock()
        self._llm = llm_provider if llm_provider is not None else (get_llm_provider(settings) if use_env_llm else None)

    # ------------------------------------------------------------ helpers
    @property
    def rca_engine_label(self) -> str:
        return f"llm:{self._llm.label}" if self._llm else "heuristic"

    def _event(self, state: DemoState, kind: str, message: str, severity: Severity | None = None) -> None:
        state.events.append(TimelineEvent(kind=kind, message=message, severity=severity))
        state.events = state.events[-MAX_EVENTS:]
        log.info("[%s] %s", kind, message)

    def _run(self, state: DemoState, run_id: str) -> PipelineRun:
        run = next((r for r in state.runs if r.run_id == run_id), None)
        if run is None:
            raise NotFoundError(f"Run {run_id} not found")
        return run

    def _profile(self, run: PipelineRun) -> DatasetProfile:
        if not run.profile_path:
            raise ConflictError(f"Run {run.run_id} produced no profile")
        return load_profile(Path(run.profile_path))

    def _incident(self, state: DemoState, incident_id: str) -> Incident:
        inc = state.incidents.get(incident_id)
        if inc is None:
            raise NotFoundError(f"Incident {incident_id} not found")
        return inc

    def _baseline(self, state: DemoState) -> tuple[PipelineRun, DatasetProfile]:
        if not state.baseline_run_id:
            raise ConflictError("No healthy baseline yet. Run the healthy pipeline first.")
        run = self._run(state, state.baseline_run_id)
        return run, self._profile(run)

    def _save_incident(self, state: DemoState, inc: Incident) -> None:
        inc.updated_at = utcnow()
        state.incidents[inc.id] = inc
        inc.report_path = str(write_report(self.settings, inc))

    # ------------------------------------------------------------ demo lifecycle
    def reset_demo(self, rows: int | None = None, seed: int | None = None) -> DemoState:
        with self._lock:
            s = self.settings
            for d in (s.data_dir / "current", s.data_dir / "baseline", s.data_dir / "generated",
                      s.profiles_dir, s.incidents_dir, s.patches_dir, s.logs_dir):
                if d.exists():
                    for child in d.iterdir():
                        if child.name == ".gitkeep":
                            continue
                        shutil.rmtree(child) if child.is_dir() else child.unlink()
            self.store.clear()
            s.ensure_dirs()
            reset_workspace(s)
            state = DemoState()
            state.dataset = write_dataset(rows or s.default_rows, seed if seed is not None else s.default_seed, s.raw_data_path)
            self._event(state, "reset", f"Demo reset. Generated {state.dataset.rows:,} synthetic customer rows (seed {state.dataset.seed}).")
            self.store.save(state)
            return state

    def generate_data(self, rows: int | None = None, seed: int | None = None) -> DemoState:
        with self._lock:
            state = self.store.load()
            s = self.settings
            state.dataset = write_dataset(rows or s.default_rows, seed if seed is not None else s.default_seed, s.raw_data_path)
            self._event(state, "data", f"Generated {state.dataset.rows:,} rows (seed {state.dataset.seed}).")
            self.store.save(state)
            return state

    def run_pipeline(self, set_baseline: bool = False) -> PipelineRun:
        with self._lock:
            state = self.store.load()
            if not self.settings.pipeline_repo.exists() or state.dataset is None:
                raise ConflictError("Demo not initialised. Click Reset Demo first.")
            if set_baseline:
                if state.injected_incident:
                    raise ConflictError("An injected incident is active; resolve it or reset the demo before capturing a baseline.")
                if not workspace_git(self.settings).is_clean():
                    raise ConflictError("Pipeline repository has uncommitted changes; cannot capture a baseline.")
            state.run_counter += 1
            run_id = f"run-{state.run_counter:04d}"
            purpose = "baseline" if set_baseline else "manual"
            run, profile = run_pipeline(self.settings, run_id, purpose=purpose)

            if set_baseline:
                if run.status != RunStatus.SUCCESS or profile is None:
                    raise ConflictError(f"Baseline run failed: {run.error}")
                run.is_baseline = True
                run.data_health = DataHealth.HEALTHY
                shutil.copyfile(self.settings.current_output_path, self.settings.baseline_output_path)
                save_profile(profile, self.settings.profiles_dir / "baseline.json")
                state.baseline_run_id = run.run_id
                state.last_detection = detect_anomalies(profile, profile, self.settings.thresholds)
                self._event(state, "baseline", f"{run_id}: healthy baseline captured ({run.rows_output:,} rows).")
            else:
                state.last_detection = None
                self._event(state, "run", f"{run_id}: pipeline finished {run.status.value} ({run.rows_output:,} rows output).")

            state.runs.append(run)
            self.store.save(state)
            return run

    def inject(self, incident_type: IncidentType) -> dict[str, str]:
        with self._lock:
            state = self.store.load()
            if not state.baseline_run_id:
                raise ConflictError("Capture a healthy baseline before injecting an incident.")
            result = inject_incident(self.settings, incident_type)
            state.injected_incident = incident_type.value
            self._event(state, "inject",
                        f"Code change committed: {result['commit'][:7]} \"{result['commit_message']}\" ({incident_type.value}).",
                        Severity.WARNING)
            self.store.save(state)
            return result

    # ------------------------------------------------------------ detection
    def detect(self) -> dict[str, Any]:
        with self._lock:
            state = self.store.load()
            if not state.runs:
                raise ConflictError("No pipeline runs yet.")
            _, base_profile = self._baseline(state)
            run = state.runs[-1]
            if run.status != RunStatus.SUCCESS:
                raise ConflictError(f"Latest run {run.run_id} FAILED; the orchestrator already reports it: {run.error}")
            report = detect_anomalies(base_profile, self._profile(run), self.settings.thresholds)
            state.last_detection = report
            run.data_health = report.data_health

            incident: Incident | None = None
            if report.data_health in (DataHealth.WARNING, DataHealth.CRITICAL):
                existing = next((i for i in state.incidents.values() if i.run_id == run.run_id), None)
                if existing:
                    incident = existing
                else:
                    state.incident_counter += 1
                    incident = Incident(
                        id=f"INC-{state.incident_counter:04d}",
                        status=IncidentStatus.DETECTED,
                        severity=report.severity or Severity.WARNING,
                        run_id=run.run_id,
                        baseline_run_id=state.baseline_run_id or "",
                        detection=report,
                    )
                    self._save_incident(state, incident)
                    self._event(state, "detect",
                                f"{incident.id} opened: data health {report.data_health.value} on {run.run_id} "
                                f"while pipeline status was {run.status.value}. {len(report.anomalies)} anomalies.",
                                incident.severity)
                run.incident_id = incident.id
                state.active_incident_id = incident.id
            else:
                self._event(state, "detect", f"{run.run_id}: data health {report.data_health.value}.")
            self.store.save(state)
            return {"detection": report, "incident": incident}

    # ------------------------------------------------------------ investigation
    def investigate(self, incident_id: str) -> Incident:
        with self._lock:
            state = self.store.load()
            inc = self._incident(state, incident_id)
            if inc.status == IncidentStatus.RESOLVED:
                raise ConflictError(f"{incident_id} is already resolved.")
            steps: list[InvestigationStep] = []

            t0 = time.perf_counter()
            base_run, base_profile = self._baseline(state)
            run = self._run(state, inc.run_id)
            cur_profile = self._profile(run)
            n_anom = len(inc.detection.anomalies)
            steps.append(InvestigationStep(
                key="data", label="Data evidence", status="done",
                detail=f"Compared {run.run_id} ({cur_profile.row_count:,} rows) with baseline {base_run.run_id} "
                       f"({base_profile.row_count:,} rows); {n_anom} anomalies.",
                duration_ms=(time.perf_counter() - t0) * 1000))

            t0 = time.perf_counter()
            git = workspace_git(self.settings)
            evidence = build_evidence(self.settings, git, inc.id, inc.detection, base_profile, cur_profile, base_run, run)
            git_ms = (time.perf_counter() - t0) * 1000
            steps.append(InvestigationStep(
                key="git", label="Git history", status="done",
                detail=f"{len(evidence.commits_since_baseline)} commit(s) since baseline commit "
                       f"{(evidence.baseline_commit or 'n/a')[:7]}; changed files: {', '.join(evidence.changed_files) or 'none'}.",
                duration_ms=git_ms))
            top = evidence.suspect_changes[0] if evidence.suspect_changes else None
            steps.append(InvestigationStep(
                key="correlate", label="Change correlation",
                status="done" if top else "skipped",
                detail=(f"Strongest match {top.file}:{top.line} (score {top.score:.2f}): {'; '.join(top.signals[:2])}."
                        if top else "No code changes to correlate."),
                duration_ms=0.0))

            t0 = time.perf_counter()
            rca = run_rca(evidence, self._llm)
            steps.append(InvestigationStep(
                key="rca", label="Root cause analysis",
                status="done" if not rca.insufficient_evidence else "failed",
                detail=f"{rca.engine}: {rca.incident_type.value} at {rca.file or 'n/a'}:{rca.line or '-'} "
                       f"(confidence {rca.confidence:.0%}).",
                duration_ms=(time.perf_counter() - t0) * 1000))

            write_text_atomic(self.settings.incidents_dir / f"{inc.id}_evidence.json", evidence.model_dump_json(indent=2))
            inc.evidence = evidence
            inc.rca = rca
            inc.investigation_steps = steps
            inc.status = IncidentStatus.ROOT_CAUSE_IDENTIFIED
            self._save_incident(state, inc)
            self._event(state, "investigate",
                        f"{inc.id}: root cause {rca.incident_type.value} in {rca.file}:{rca.line} "
                        f"(confidence {rca.confidence:.0%}, engine {rca.engine}).", inc.severity)
            self.store.save(state)
            return inc

    # ------------------------------------------------------------ remediation
    def propose_fix(self, incident_id: str) -> Incident:
        with self._lock:
            state = self.store.load()
            inc = self._incident(state, incident_id)
            if inc.rca is None or inc.evidence is None:
                raise ConflictError("Investigate the incident before generating a fix.")
            if inc.status in (IncidentStatus.FIX_APPLIED, IncidentStatus.RESOLVED):
                raise ConflictError(f"{incident_id} already has an applied fix.")
            attempt = 1 + (0 if inc.patch is None else int(inc.patch.patch_id.rsplit("-P", 1)[-1]))
            patch = generate_patch(self.settings, inc.id, f"{inc.id}-P{attempt}", inc.rca, inc.evidence)
            inc.patch = patch
            inc.status = IncidentStatus.FIX_PROPOSED
            self._save_incident(state, inc)
            self._event(state, "fix", f"{inc.id}: patch {patch.patch_id} proposed for {patch.file}. Awaiting approval.")
            self.store.save(state)
            return inc

    def reject_fix(self, incident_id: str) -> Incident:
        with self._lock:
            state = self.store.load()
            inc = self._incident(state, incident_id)
            if inc.patch is None or inc.patch.status != "PROPOSED":
                raise ConflictError("There is no proposed patch to reject.")
            inc.patch = inc.patch.model_copy(update={"status": "REJECTED"})
            inc.status = IncidentStatus.FIX_REJECTED
            self._save_incident(state, inc)
            self._event(state, "fix", f"{inc.id}: patch {inc.patch.patch_id} rejected by operator.")
            self.store.save(state)
            return inc

    def apply_fix(self, incident_id: str) -> Incident:
        with self._lock:
            state = self.store.load()
            inc = self._incident(state, incident_id)
            if inc.patch is None:
                raise ConflictError("Generate a fix before applying it.")
            itype = inc.rca.incident_type.value if inc.rca else "incident"
            inc.patch = apply_patch(self.settings, inc.patch, itype)
            inc.status = IncidentStatus.FIX_APPLIED
            self._save_incident(state, inc)
            self._event(state, "apply", f"{inc.id}: patch applied and committed as {inc.patch.applied_commit[:7]}.")
            self.store.save(state)
            return inc

    # ------------------------------------------------------------ validation
    def validate(self, incident_id: str) -> Incident:
        with self._lock:
            state = self.store.load()
            inc = self._incident(state, incident_id)
            if inc.status == IncidentStatus.RESOLVED:
                raise ConflictError(f"{incident_id} is already resolved.")
            _, base_profile = self._baseline(state)

            state.run_counter += 1
            run_id = f"run-{state.run_counter:04d}"
            run, profile = run_pipeline(self.settings, run_id, purpose="validation")
            detection = detect_anomalies(base_profile, profile, self.settings.thresholds) if profile else None
            if detection:
                run.data_health = detection.data_health
                state.last_detection = detection
            run.incident_id = inc.id
            state.runs.append(run)

            result = validate_incident(self.settings, inc, run, profile, base_profile, detection)
            inc.validation = result
            if result.passed:
                inc.status = IncidentStatus.RESOLVED
                inc.resolved_at = utcnow()
                state.injected_incident = None
                self._event(state, "resolved", f"{inc.id} RESOLVED: all {len(result.checks)} validation checks passed on {run_id}.")
            else:
                inc.status = IncidentStatus.VALIDATION_FAILED
                failed = [c.name for c in result.checks if not c.passed]
                self._event(state, "validate", f"{inc.id}: validation FAILED on {run_id} ({', '.join(failed)}).",
                            Severity.CRITICAL)
            self._save_incident(state, inc)
            self.store.save(state)
            return inc

    # ------------------------------------------------------------ reads
    def get_incident(self, incident_id: str) -> Incident:
        return self._incident(self.store.load(), incident_id)

    def report_markdown(self, incident_id: str) -> str:
        state = self.store.load()
        inc = self._incident(state, incident_id)
        path = write_report(self.settings, inc)
        return path.read_text(encoding="utf-8")

    def dashboard(self) -> dict[str, Any]:
        state = self.store.load()
        baseline_profile = latest_profile = None
        if state.baseline_run_id:
            try:
                baseline_profile = self._profile(self._run(state, state.baseline_run_id))
            except (ConflictError, NotFoundError, OSError):
                pass
        latest = state.runs[-1] if state.runs else None
        if latest and latest.profile_path:
            try:
                latest_profile = self._profile(latest)
            except (ConflictError, OSError):
                pass

        repo: dict[str, Any] = {"path": str(self.settings.pipeline_repo), "initialised": False}
        git = workspace_git(self.settings)
        if git.is_repo():
            repo.update(
                initialised=True,
                head=git.head(),
                clean=git.is_clean(),
                recent_commits=[c.model_dump() for c in git.recent_commits(8)],
            )

        active = state.incidents.get(state.active_incident_id) if state.active_incident_id else None
        return {
            "dataset": state.dataset,
            "runs": state.runs,
            "latest_run": latest,
            "baseline_run_id": state.baseline_run_id,
            "baseline_profile": baseline_profile,
            "latest_profile": latest_profile,
            "last_detection": state.last_detection,
            "active_incident": active,
            "incidents": sorted(state.incidents.values(), key=lambda i: i.created_at, reverse=True),
            "injected_incident": state.injected_incident,
            "events": list(reversed(state.events[-50:])),
            "repository": repo,
            "rca_engine": self.rca_engine_label,
            "incident_types": list_scenarios(),
        }
