"""Shared fixtures. Every test runs against an isolated DATASENTINEL_HOME with no LLM."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings
from app.services.workflow import DataSentinelService

TEST_ROWS = 6000


@pytest.fixture
def settings(tmp_path, monkeypatch) -> Settings:
    monkeypatch.setenv("DATASENTINEL_HOME", str(tmp_path))
    monkeypatch.setenv("DATASENTINEL_DEFAULT_ROWS", str(TEST_ROWS))
    monkeypatch.setenv("LLM_PROVIDER", "heuristic")
    get_settings.cache_clear()
    s = get_settings()
    yield s
    get_settings.cache_clear()


@pytest.fixture
def service(settings) -> DataSentinelService:
    return DataSentinelService(settings, use_env_llm=False)


@pytest.fixture
def baseline_service(service) -> DataSentinelService:
    service.reset_demo()
    service.run_pipeline(set_baseline=True)
    return service


@pytest.fixture
def filter_incident(baseline_service):
    """Service with a filter regression injected, run and detected."""
    from app.core.models import IncidentType

    baseline_service.inject(IncidentType.FILTER_REGRESSION)
    run = baseline_service.run_pipeline()
    result = baseline_service.detect()
    return baseline_service, run, result
