"""Runs all anomaly rules and derives overall data health."""

from __future__ import annotations

from app.core.config import DetectionThresholds
from app.core.models import DataHealth, DatasetProfile, DetectionReport, Severity
from app.detection.rules import ALL_RULES


def detect_anomalies(
    baseline: DatasetProfile, current: DatasetProfile, thresholds: DetectionThresholds
) -> DetectionReport:
    anomalies = [a for rule in ALL_RULES for a in rule(baseline, current, thresholds)]
    anomalies.sort(key=lambda a: (-a.severity.rank, a.rule, a.id))

    severity = max((a.severity for a in anomalies), key=lambda s: s.rank, default=None)
    if severity == Severity.CRITICAL:
        health = DataHealth.CRITICAL
    elif severity == Severity.WARNING:
        health = DataHealth.WARNING
    else:
        health = DataHealth.HEALTHY

    change = (current.row_count - baseline.row_count) / baseline.row_count if baseline.row_count else 0.0
    counts = {s: sum(1 for a in anomalies if a.severity == s) for s in Severity}
    if health == DataHealth.HEALTHY:
        summary = "No material anomalies versus the healthy baseline."
    else:
        headline = "; ".join(a.title for a in anomalies[:3])
        summary = (
            f"{counts[Severity.CRITICAL]} critical, {counts[Severity.WARNING]} warning, "
            f"{counts[Severity.INFO]} info anomalies. {headline}."
        )

    return DetectionReport(
        run_id=current.run_id,
        baseline_run_id=baseline.run_id,
        data_health=health,
        severity=severity,
        anomalies=anomalies,
        row_count_baseline=baseline.row_count,
        row_count_current=current.row_count,
        row_count_change_pct=round(change, 6),
        summary=summary,
    )
