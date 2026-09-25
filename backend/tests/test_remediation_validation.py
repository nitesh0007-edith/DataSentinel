import pytest

from app.core.errors import ConflictError, UnsafeOperationError
from app.core.models import IncidentStatus, IncidentType
from app.investigation.git_analyzer import GitError
from app.pipeline.workspace import resolve_in_repo


def _to_fix(filter_incident):
    svc, _, result = filter_incident
    inc = svc.investigate(result["incident"].id)
    return svc, svc.propose_fix(inc.id)


def test_fix_is_proposed_not_applied(filter_incident):
    svc, inc = _to_fix(filter_incident)
    assert inc.status == IncidentStatus.FIX_PROPOSED
    assert '-    df = df[df["country"] == "UK"]' in inc.patch.diff
    assert '+    df = df[df["country"].isin(["UK", "Germany", "Italy"])]' in inc.patch.diff
    source = (svc.settings.pipeline_repo / "pipelines/customer_transform.py").read_text()
    assert 'df["country"] == "UK"' in source  # nothing changed on disk yet


def test_validation_without_fix_fails(filter_incident):
    svc, inc = _to_fix(filter_incident)
    inc = svc.validate(inc.id)
    assert inc.status == IncidentStatus.VALIDATION_FAILED
    failed = {c.name for c in inc.validation.checks if not c.passed}
    assert {"Row count restored", "Germany restored", "Italy restored", "Repository tests"} <= failed


def test_healthy_output_without_approved_patch_cannot_resolve(filter_incident):
    svc, inc = _to_fix(filter_incident)
    target = svc.settings.pipeline_repo / inc.patch.file
    target.write_text((svc.settings.patches_dir / f"{inc.patch.patch_id}.proposed").read_text())
    inc = svc.validate(inc.id)
    assert inc.status == IncidentStatus.VALIDATION_FAILED
    assert inc.validation.detection.data_health.value == "HEALTHY"
    assert next(c for c in inc.validation.checks if c.name == "Approved patch applied").passed is False


def test_full_golden_path_resolves(filter_incident):
    svc, inc = _to_fix(filter_incident)
    inc = svc.apply_fix(inc.id)
    assert inc.status == IncidentStatus.FIX_APPLIED
    inc = svc.validate(inc.id)
    assert inc.validation.passed, [c for c in inc.validation.checks if not c.passed]
    assert inc.status == IncidentStatus.RESOLVED
    names = {c.name for c in inc.validation.checks}
    assert {"Pipeline completed", "Row count restored", "Germany restored", "Italy restored",
            "Schema passed", "Repository tests"} <= names
    report = svc.report_markdown(inc.id)
    assert "RESOLVED" in report and "customer_transform.py" in report


def test_apply_refuses_if_file_changed(filter_incident):
    svc, inc = _to_fix(filter_incident)
    target = svc.settings.pipeline_repo / "pipelines/customer_transform.py"
    target.write_text(target.read_text() + "\n# local edit\n")
    with pytest.raises(ConflictError):
        svc.apply_fix(inc.id)


def test_apply_refuses_unrelated_workspace_changes(filter_incident):
    svc, inc = _to_fix(filter_incident)
    target = svc.settings.pipeline_repo / inc.patch.file
    before = target.read_text()
    (svc.settings.pipeline_repo / "unrelated.txt").write_text("keep me")
    with pytest.raises(ConflictError, match="uncommitted changes"):
        svc.apply_fix(inc.id)
    assert target.read_text() == before


def test_apply_restores_source_if_commit_fails(filter_incident, monkeypatch):
    svc, inc = _to_fix(filter_incident)
    target = svc.settings.pipeline_repo / inc.patch.file
    before = target.read_text()

    def fail_commit(*args):
        raise GitError("simulated commit failure")

    monkeypatch.setattr("app.investigation.git_analyzer.GitRepository.commit_staged", fail_commit)
    with pytest.raises(GitError, match="simulated"):
        svc.apply_fix(inc.id)
    assert target.read_text() == before
    assert svc.store.load().incidents[inc.id].patch.status == "PROPOSED"


def test_reset_refuses_symlinked_data_directory(service, tmp_path):
    managed = service.settings.data_dir / "current"
    managed.rmdir()
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    marker = unrelated / "keep.txt"
    marker.write_text("keep")
    managed.symlink_to(unrelated, target_is_directory=True)

    with pytest.raises(UnsafeOperationError, match="symlinked"):
        service.reset_demo()
    assert marker.read_text() == "keep"


def test_rejected_patch_cannot_be_applied(filter_incident):
    svc, inc = _to_fix(filter_incident)
    svc.reject_fix(inc.id)
    with pytest.raises(ConflictError):
        svc.apply_fix(inc.id)


@pytest.mark.parametrize("path", ["../../etc/passwd", "/tmp/x.py", ".git/config"])
def test_patch_paths_confined_to_repo(settings, path):
    settings.pipeline_repo.mkdir(parents=True, exist_ok=True)
    with pytest.raises(UnsafeOperationError):
        resolve_in_repo(settings.pipeline_repo, path)


@pytest.mark.parametrize("itype", [t for t in IncidentType if t not in (IncidentType.UNKNOWN, IncidentType.FILTER_REGRESSION)])
def test_other_incident_types_resolve(baseline_service, itype):
    svc = baseline_service
    svc.inject(itype)
    svc.run_pipeline()
    inc = svc.detect()["incident"]
    assert inc is not None
    inc = svc.investigate(inc.id)
    assert inc.rca.incident_type == itype
    svc.propose_fix(inc.id)
    svc.apply_fix(inc.id)
    inc = svc.validate(inc.id)
    assert inc.status == IncidentStatus.RESOLVED, [c for c in inc.validation.checks if not c.passed]
