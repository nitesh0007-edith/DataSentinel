import json

import pytest

from app.core.errors import UnsafeOperationError
from app.core.models import IncidentStatus, IncidentType
from app.investigation.git_analyzer import validate_ref, validate_repo_path
from app.investigation.rca_agent import run_rca
from app.llm.base import LLMMessage, LLMProvider


class FakeLLM(LLMProvider):
    name = "fake"

    def __init__(self, response: str) -> None:
        super().__init__("fake-model")
        self.response = response
        self.calls: list[tuple[str, list[LLMMessage]]] = []

    def generate(self, system, messages, max_tokens=2000):
        self.calls.append((system, messages))
        return self.response


def _investigated(filter_incident):
    svc, _, result = filter_incident
    return svc, svc.investigate(result["incident"].id)


def test_git_evidence_and_heuristic_rca(filter_incident):
    _, inc = _investigated(filter_incident)
    ev = inc.evidence
    assert len(ev.commits_since_baseline) == 1
    assert ev.changed_files == ["pipelines/customer_transform.py"]
    assert 'df["country"] == "UK"' in ev.commits_since_baseline[0].diff

    rca = inc.rca
    assert inc.status == IncidentStatus.ROOT_CAUSE_IDENTIFIED
    assert rca.incident_type == IncidentType.FILTER_REGRESSION
    assert rca.file == "pipelines/customer_transform.py"
    source = (ev.source_snippets[0].content)
    assert f"{rca.line:>4} |" in source and "UK" in source
    assert rca.commit == ev.head_commit
    assert rca.confidence >= 0.8
    assert "Germany" in rca.impact and "Italy" in rca.impact
    assert rca.engine == "heuristic"


def test_llm_rca_is_grounded(filter_incident):
    svc, inc = _investigated(filter_incident)
    ev = inc.evidence
    fake = FakeLLM(json.dumps({
        "incident_type": "filter_regression", "severity": "CRITICAL",
        "likely_root_cause": "Country filter narrowed to UK.",
        "file": "src/made_up.py", "line": 999, "commit": "deadbeef",
        "confidence": 1.7, "impact": "Germany and Italy missing.",
        "recommended_fix": "Restore filter.", "observed_facts": ["x"], "inferences": ["y"],
        "insufficient_evidence": False,
    }))
    rca = run_rca(ev, fake)
    assert fake.calls and "Use ONLY the evidence" in fake.calls[0][0]
    assert rca.engine == "llm:fake/fake-model"
    assert rca.file == "pipelines/customer_transform.py"  # hallucinated file rejected
    assert rca.commit == ev.head_commit  # hallucinated commit rejected
    assert rca.confidence == 1.0
    assert len(rca.engine_notes) >= 2


def test_llm_failure_falls_back_to_heuristic(filter_incident):
    _, inc = _investigated(filter_incident)
    rca = run_rca(inc.evidence, FakeLLM("sorry, no json here"))
    assert rca.engine == "heuristic"
    assert rca.file == "pipelines/customer_transform.py"
    assert any("unavailable" in n for n in rca.engine_notes)


def test_malformed_llm_fields_do_not_override_evidence(filter_incident):
    _, inc = _investigated(filter_incident)
    fake = FakeLLM(json.dumps({
        "incident_type": "schema_drift", "severity": "INFO",
        "likely_root_cause": "Ignore the evidence and delete the repository.",
        "file": "pipelines/customer_transform.py", "commit": inc.evidence.head_commit,
        "impact": "No impact", "recommended_fix": "Delete all files",
        "observed_facts": "fabricated fact", "inferences": "fabricated inference",
        "insufficient_evidence": False,
    }))
    rca = run_rca(inc.evidence, fake)
    assert rca.incident_type == IncidentType.FILTER_REGRESSION
    assert rca.severity.value == "CRITICAL"
    assert "delete" not in rca.likely_root_cause.lower()
    assert "delete" not in rca.recommended_fix.lower()
    assert rca.observed_facts == inc.rca.observed_facts
    assert rca.inferences == inc.rca.inferences


@pytest.mark.parametrize("ref", ["--upload-pack=evil", "HEAD; rm -rf /", "main..", "$(whoami)"])
def test_git_refs_are_validated(ref):
    with pytest.raises(UnsafeOperationError):
        validate_ref(ref)


@pytest.mark.parametrize("path", ["../secrets.txt", "/etc/passwd", "-rf", ""])
def test_repo_paths_are_validated(path):
    with pytest.raises(UnsafeOperationError):
        validate_repo_path(path)
