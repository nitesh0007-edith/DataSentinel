"""The core demo: a filter regression leaves the pipeline SUCCESSFUL but drops data."""

from app.core.models import DataHealth, IncidentType, RunStatus, Severity


def test_healthy_baseline_keeps_all_countries(baseline_service):
    state = baseline_service.store.load()
    run = state.runs[-1]
    assert run.status == RunStatus.SUCCESS and run.is_baseline
    assert run.rows_output == run.rows_input
    profile = baseline_service.dashboard()["baseline_profile"]
    assert set(profile.columns["country"].frequencies) == {"UK", "Germany", "Italy"}


def test_filter_regression_succeeds_but_loses_data(baseline_service):
    inj = baseline_service.inject(IncidentType.FILTER_REGRESSION)
    assert inj["file"] == "pipelines/customer_transform.py"
    run = baseline_service.run_pipeline()
    assert run.status == RunStatus.SUCCESS  # the orchestrator is happy...
    assert run.rows_output < run.rows_input * 0.6  # ...but most rows are gone
    latest = baseline_service.dashboard()["latest_profile"]
    assert set(latest.columns["country"].frequencies) == {"UK"}


def test_detection_opens_critical_incident(filter_incident):
    _, _, result = filter_incident
    det = result["detection"]
    assert det.data_health == DataHealth.CRITICAL
    assert det.severity == Severity.CRITICAL
    missing = {a.details["value"] for a in det.anomalies if a.rule == "category_disappearance"}
    assert missing == {"Germany", "Italy"}
    assert any(a.rule == "row_count" and a.severity == Severity.CRITICAL for a in det.anomalies)
    assert result["incident"].id == "INC-0001"


def test_inject_twice_is_rejected(baseline_service):
    import pytest

    from app.core.errors import ConflictError

    baseline_service.inject(IncidentType.FILTER_REGRESSION)
    with pytest.raises(ConflictError):
        baseline_service.inject(IncidentType.SCHEMA_DRIFT)
