"""RAW -> BRONZE -> SILVER -> GOLD pipeline simulator.

Like a real orchestrator, the runner only knows whether the code *executed*.
It reports SUCCESS whenever no exception is raised, regardless of whether the
produced data is correct. That gap is what DataSentinel exists to close.
"""

from __future__ import annotations

import importlib.util
import time
import uuid
from datetime import datetime, timezone
from types import ModuleType

import pandas as pd

from app.core.config import Settings
from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.core.models import DatasetProfile, PipelineRun, RunStatus, StageMetrics
from app.pipeline.workspace import resolve_in_repo, workspace_git
from app.profiling.profiler import profile_dataframe, save_profile

log = get_logger("runner")


def _load_transform_module(settings: Settings) -> ModuleType:
    path = resolve_in_repo(settings.pipeline_repo, settings.transform_module_path)
    if not path.exists():
        raise ConflictError("Pipeline code not found. Reset the demo first.")
    # Unique module name so every run executes the file as it is *now* on disk.
    spec = importlib.util.spec_from_file_location(f"ds_transform_{uuid.uuid4().hex}", path)
    if spec is None or spec.loader is None:
        raise ConflictError(f"Cannot load transformation module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pipeline(settings: Settings, run_id: str, purpose: str = "manual") -> tuple[PipelineRun, DatasetProfile | None]:
    if not settings.raw_data_path.exists():
        raise ConflictError("No raw dataset found. Reset the demo or generate data first.")

    logs: list[str] = []

    def emit(msg: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        line = f"{stamp} [{run_id}] {msg}"
        logs.append(line)
        log.info(msg)

    git = workspace_git(settings)
    commit = commit_msg = None
    try:
        info = git.commit_info("HEAD")
        commit, commit_msg = info.sha, info.message
    except Exception as exc:  # git metadata is optional for a run
        emit(f"WARN git metadata unavailable: {exc}")

    started = time.perf_counter()
    stages: list[StageMetrics] = []
    status = RunStatus.SUCCESS
    error: str | None = None
    gold: pd.DataFrame | None = None
    rows_input = 0

    emit(f"Pipeline started (purpose={purpose}, commit={commit[:7] if commit else 'n/a'})")
    try:
        t0 = time.perf_counter()
        raw = pd.read_csv(settings.raw_data_path)
        rows_input = len(raw)
        stages.append(StageMetrics(stage="RAW", rows_in=rows_input, rows_out=rows_input,
                                   duration_ms=(time.perf_counter() - t0) * 1000))
        emit(f"RAW    loaded {rows_input:,} rows from {settings.raw_data_path.name}")

        module = _load_transform_module(settings)
        df = raw
        for stage, fn_name in (("BRONZE", "to_bronze"), ("SILVER", "to_silver"), ("GOLD", "to_gold")):
            t0 = time.perf_counter()
            rows_in = len(df)
            df = getattr(module, fn_name)(df)
            stages.append(StageMetrics(stage=stage, rows_in=rows_in, rows_out=len(df),
                                       duration_ms=(time.perf_counter() - t0) * 1000))
            emit(f"{stage:<6} {fn_name}: {rows_in:,} -> {len(df):,} rows")
        gold = df
        settings.current_output_path.parent.mkdir(parents=True, exist_ok=True)
        gold.to_csv(settings.current_output_path, index=False)
        emit(f"GOLD   written to {settings.current_output_path.name}")
    except Exception as exc:
        status = RunStatus.FAILED
        error = f"{type(exc).__name__}: {exc}"
        emit(f"ERROR  {error}")

    duration_ms = (time.perf_counter() - started) * 1000
    profile: DatasetProfile | None = None
    run = PipelineRun(
        run_id=run_id,
        status=status,
        rows_input=rows_input,
        rows_output=len(gold) if gold is not None else 0,
        duration_ms=round(duration_ms, 1),
        stages=stages,
        git_commit=commit,
        git_commit_message=commit_msg,
        error=error,
        purpose=purpose,
    )

    if gold is not None:
        profile = profile_dataframe(gold, run_id, settings.thresholds)
        profile_path = settings.profiles_dir / f"{run_id}.json"
        save_profile(profile, profile_path)
        run.profile_path = str(profile_path)
        run.output_path = str(settings.current_output_path)
        run.schema_snapshot = profile.schema_map
        total_cells = max(profile.row_count * profile.column_count, 1)
        run.quality_metrics = {
            "null_pct": round(sum(c.null_count for c in profile.columns.values()) / total_cells, 6),
            "duplicate_pct": profile.duplicate_pct,
            "duplicate_count": float(profile.duplicate_count),
            "column_count": float(profile.column_count),
        }
        emit(f"Profile saved ({profile.row_count:,} rows, {profile.column_count} columns)")

    emit(f"Pipeline finished: status={status.value} in {duration_ms:,.0f} ms")
    run.logs = logs
    (settings.logs_dir / f"{run_id}.log").write_text("\n".join(logs) + "\n", encoding="utf-8")
    return run, profile
