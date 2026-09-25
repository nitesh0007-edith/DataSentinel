"""Post-remediation validation. An incident is RESOLVED only if every check passes."""

from __future__ import annotations

import os
import subprocess
import sys

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.models import (
    DataHealth,
    DatasetProfile,
    DetectionReport,
    Incident,
    PipelineRun,
    RunStatus,
    Severity,
    ValidationCheck,
    ValidationResult,
)

log = get_logger("validation")


def run_repository_tests(settings: Settings) -> ValidationCheck:
    """Run the pipeline repository's own test suite (fixed command, no user input)."""
    tests_dir = settings.pipeline_repo / "tests"
    if not tests_dir.is_dir():
        return ValidationCheck(name="Repository tests", passed=False, detail="No tests directory in pipeline repository.")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
            cwd=settings.pipeline_repo,
            capture_output=True,
            text=True,
            timeout=settings.test_timeout_seconds,
            shell=False,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ValidationCheck(name="Repository tests", passed=False, detail="Test run timed out.")
    tail = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    return ValidationCheck(name="Repository tests", passed=proc.returncode == 0, detail=tail)


def validate_incident(
    settings: Settings,
    incident: Incident,
    run: PipelineRun,
    profile: DatasetProfile | None,
    baseline: DatasetProfile,
    detection: DetectionReport | None,
) -> ValidationResult:
    t = settings.thresholds
    checks: list[ValidationCheck] = []

    checks.append(ValidationCheck(
        name="Approved patch applied",
        passed=incident.patch is not None and incident.patch.status == "APPLIED",
        detail="Proposed patch was approved and committed." if incident.patch and incident.patch.status == "APPLIED"
        else "Apply the proposed patch before the incident can be resolved.",
    ))

    checks.append(ValidationCheck(
        name="Pipeline completed",
        passed=run.status == RunStatus.SUCCESS,
        detail=f"Run {run.run_id} finished with status {run.status.value}" + (f": {run.error}" if run.error else "."),
    ))

    if profile is None or detection is None:
        checks.append(ValidationCheck(name="Data profile", passed=False, detail="No output to profile."))
        return ValidationResult(run_id=run.run_id, passed=False, checks=checks, detection=detection)

    change = abs(profile.row_count - baseline.row_count) / baseline.row_count if baseline.row_count else 0.0
    checks.append(ValidationCheck(
        name="Row count restored",
        passed=change < t.row_count_warning,
        detail=f"{profile.row_count:,} rows vs baseline {baseline.row_count:,} ({change:.2%} difference).",
    ))

    # Every category value that disappeared during the incident must be back.
    for a in incident.detection.anomalies:
        if a.rule != "category_disappearance" or not a.column:
            continue
        value = a.details.get("value")
        col = profile.columns.get(a.column)
        share = (col.frequencies or {}).get(value, 0.0) if col else 0.0
        count = round(share * (profile.row_count - (col.null_count if col else 0)))
        checks.append(ValidationCheck(
            name=f"{value} restored",
            passed=share > 0,
            detail=f"{a.column}='{value}': {count:,} rows ({share:.1%}); baseline {a.baseline_value:.1%}.",
        ))

    schema_issues = [a for a in detection.anomalies if a.rule == "schema"]
    checks.append(ValidationCheck(
        name="Schema passed",
        passed=not schema_issues,
        detail="Output schema matches baseline." if not schema_issues else "; ".join(a.title for a in schema_issues),
    ))

    quality_rules = {"null_rate", "duplicates"}
    quality_issues = [a for a in detection.anomalies if a.rule in quality_rules and a.severity != Severity.INFO]
    checks.append(ValidationCheck(
        name="Data-quality checks passed",
        passed=not quality_issues,
        detail="Null and duplicate rates within thresholds." if not quality_issues
        else "; ".join(a.title for a in quality_issues),
    ))

    blocking = [a for a in detection.anomalies if a.severity != Severity.INFO]
    checks.append(ValidationCheck(
        name="Regression checks passed",
        passed=detection.data_health == DataHealth.HEALTHY,
        detail=f"Data health {detection.data_health.value}; {len(blocking)} warning/critical anomalies vs baseline.",
    ))

    checks.append(run_repository_tests(settings))

    passed = all(c.passed for c in checks)
    log.info("Validation for %s: %s", incident.id, "PASSED" if passed else "FAILED")
    return ValidationResult(run_id=run.run_id, passed=passed, checks=checks, detection=detection)
