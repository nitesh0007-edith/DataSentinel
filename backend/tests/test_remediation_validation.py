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


# ------------------------------------------------------------------ rollback tests

def _to_validation_failed(filter_incident, monkeypatch):
    """Apply fix then force validation to fail via a failing repo-test check."""
    svc, inc = _to_fix(filter_incident)
    inc = svc.apply_fix(inc.id)
    assert inc.status == IncidentStatus.FIX_APPLIED

    from app.core.models import ValidationCheck

    # Monkeypatch the repository-test runner so validation always fails.
    monkeypatch.setattr(
        "app.validation.validator.run_repository_tests",
        lambda _settings: ValidationCheck(
            name="Repository tests", passed=False, detail="injected failure for test"
        ),
    )
    inc = svc.validate(inc.id)
    assert inc.status == IncidentStatus.VALIDATION_FAILED
    return svc, inc


def test_rollback_restores_source_and_returns_retryable(filter_incident, monkeypatch):
    svc, inc = _to_validation_failed(filter_incident, monkeypatch)

    original_source = (svc.settings.patches_dir / f"{inc.patch.patch_id}.orig").read_text()
    inc = svc.rollback_fix(inc.id)

    # Status reset to ROOT_CAUSE_IDENTIFIED so operator can retry
    assert inc.status == IncidentStatus.ROOT_CAUSE_IDENTIFIED
    # Patch recorded as rolled back
    assert inc.patch.status == "ROLLED_BACK"
    assert inc.patch.rolled_back_at is not None
    assert inc.patch.rollback_commit is not None

    # Disk: source file matches original (pre-fix) content
    target = svc.settings.pipeline_repo / inc.patch.file
    assert target.read_text(encoding="utf-8") == original_source

    # Repo is clean after rollback commit
    from app.pipeline.workspace import workspace_git
    git = workspace_git(svc.settings)
    assert git.is_clean()

    # Validation evidence is preserved
    assert inc.validation is not None
    assert not inc.validation.passed
    failed_names = {c.name for c in inc.validation.checks if not c.passed}
    assert "Repository tests" in failed_names


def test_rollback_git_history_records_recovery(filter_incident, monkeypatch):
    svc, inc = _to_validation_failed(filter_incident, monkeypatch)
    inc = svc.rollback_fix(inc.id)

    from app.pipeline.workspace import workspace_git
    git = workspace_git(svc.settings)
    recent = git.recent_commits(5)
    # Most recent commit should be the rollback
    assert "roll back" in recent[0].message.lower()
    assert inc.patch.patch_id in recent[0].message


def test_rollback_before_apply_is_rejected(filter_incident):
    svc, inc = _to_fix(filter_incident)
    # Incident is FIX_PROPOSED — not yet applied
    with pytest.raises(ConflictError, match="only allowed after validation has failed"):
        svc.rollback_fix(inc.id)


def test_rollback_before_validation_is_rejected(filter_incident):
    svc, inc = _to_fix(filter_incident)
    inc = svc.apply_fix(inc.id)
    # Incident is FIX_APPLIED — not yet validated
    with pytest.raises(ConflictError, match="only allowed after validation has failed"):
        svc.rollback_fix(inc.id)


def test_double_rollback_rejected(filter_incident, monkeypatch):
    svc, inc = _to_validation_failed(filter_incident, monkeypatch)
    inc = svc.rollback_fix(inc.id)
    # After rollback incident is ROOT_CAUSE_IDENTIFIED — re-attempting rollback must fail
    with pytest.raises(ConflictError, match="only allowed after validation has failed"):
        svc.rollback_fix(inc.id)


def test_rollback_resolved_incident_rejected(filter_incident):
    svc, inc = _to_fix(filter_incident)
    inc = svc.apply_fix(inc.id)
    inc = svc.validate(inc.id)
    assert inc.status == IncidentStatus.RESOLVED
    with pytest.raises(ConflictError, match="already resolved"):
        svc.rollback_fix(inc.id)


def test_rollback_allows_retry_and_resolve(filter_incident, monkeypatch):
    """Full retryable path: apply → validate (forced fail) → rollback → apply again → validate (real)."""
    svc, inc = _to_validation_failed(filter_incident, monkeypatch)
    inc = svc.rollback_fix(inc.id)
    assert inc.status == IncidentStatus.ROOT_CAUSE_IDENTIFIED

    # Undo the monkeypatch so the real test runner is used for the retry validation.
    monkeypatch.undo()

    # Propose and apply a new fix (attempt 2)
    inc = svc.propose_fix(inc.id)
    assert inc.patch.patch_id.endswith("-P2")
    inc = svc.apply_fix(inc.id)
    assert inc.status == IncidentStatus.FIX_APPLIED

    # Now validate for real (should resolve)
    inc = svc.validate(inc.id)
    assert inc.status == IncidentStatus.RESOLVED, [c for c in inc.validation.checks if not c.passed]


# ------------------------------------------------------------------ Sub-Task C: report-write ordering

def test_state_saved_even_when_report_write_fails(filter_incident, monkeypatch):
    """A report-write failure must not prevent the incident state from being persisted."""
    svc, _, result = filter_incident
    inc = svc.investigate(result["incident"].id)
    inc_id = inc.id

    call_count = {"n": 0}

    def failing_write(settings, inc):
        call_count["n"] += 1
        raise OSError("simulated disk full")

    # Patch the name as imported into workflow.py (not the module attribute)
    import app.services.workflow as wf_module
    monkeypatch.setattr(wf_module, "write_report", failing_write)

    # propose_fix calls _write_report_safe after store.save — should not raise
    inc = svc.propose_fix(inc_id)

    # State must be persisted correctly despite the report-write failure
    loaded = svc.store.load()
    assert loaded.incidents[inc_id].status.value == "FIX_PROPOSED"
    assert call_count["n"] >= 1  # write_report was called (and failed gracefully)


# ------------------------------------------------------------------ Sub-Task D: idempotency + worker warning

def test_double_apply_is_idempotent(filter_incident):
    """A second apply_fix call on an already-applied incident returns the same state without error."""
    svc, inc = _to_fix(filter_incident)
    inc1 = svc.apply_fix(inc.id)
    assert inc1.status == IncidentStatus.FIX_APPLIED

    # Second call — must not raise, must return the already-applied incident
    inc2 = svc.apply_fix(inc.id)
    assert inc2.status == IncidentStatus.FIX_APPLIED
    assert inc2.patch.status == "APPLIED"
    assert inc2.patch.applied_commit == inc1.patch.applied_commit  # same commit, not a second one

    # Repo: only one bot commit was made
    from app.pipeline.workspace import workspace_git
    git = workspace_git(svc.settings)
    bot_commits = [c for c in git.recent_commits(10) if "DataSentinel" in c.message]
    fix_commits = [c for c in bot_commits if c.message.startswith("fix:")]
    assert len(fix_commits) == 1


def test_startup_warns_on_multi_worker(monkeypatch, caplog):
    """_warn_if_multi_worker logs a warning when WEB_CONCURRENCY > 1 is detected."""
    import logging
    import app.main as main_module

    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    with caplog.at_level(logging.WARNING, logger="datasentinel.api"):
        main_module._warn_if_multi_worker()
    assert "UNSAFE CONFIGURATION" in caplog.text
    assert "WEB_CONCURRENCY=4" in caplog.text
