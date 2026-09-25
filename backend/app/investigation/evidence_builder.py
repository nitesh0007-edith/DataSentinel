"""Builds the structured evidence package the RCA stage reasons over.

The RCA engine (heuristic or LLM) only ever sees this package, never the
repository at large. Correlating anomalies with diff hunks is deterministic.
"""

from __future__ import annotations

import re

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.models import (
    Anomaly,
    CommitEvidence,
    DatasetProfile,
    DetectionReport,
    DiffHunk,
    EvidencePackage,
    PipelineRun,
    SourceSnippet,
    SuspectChange,
)
from app.detection.rules import schema_diff
from app.investigation.git_analyzer import GitRepository
from app.pipeline.workspace import resolve_in_repo

log = get_logger("evidence")

SNIPPET_CONTEXT = 6
MAX_SNIPPETS = 6

# Code patterns that plausibly explain each anomaly rule.
RULE_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "category_disappearance": [(r"df\[df\[", "row filter"), (r"\.isin\(|==|!=", "equality/membership predicate")],
    "category_shift": [(r"df\[df\[", "row filter")],
    "row_count": [(r"df\[df\[|\.query\(|dropna|drop_duplicates", "row-reducing operation"),
                  (r"concat|append|merge", "row-adding operation")],
    "null_rate": [(r"\.where\(|\.mask\(|None|np\.nan|pd\.NA", "value masking / null assignment")],
    "duplicates": [(r"concat|append|sample\(|merge", "row duplication operation")],
    "schema": [(r"rename\(|drop\(columns|columns=", "column rename/drop")],
    "numeric_drift": [(r"[*/]\s*\d+|\.round\(|astype\(", "numeric transformation")],
}


def _hunk_tokens(hunk: DiffHunk) -> str:
    return "\n".join(line.content for line in hunk.lines if line.kind in "+-")


def score_hunk(hunk: DiffHunk, commit_sha: str, anomalies: list[Anomaly]) -> SuspectChange:
    changed = _hunk_tokens(hunk)
    signals: list[str] = []
    score = 0.0

    columns = {a.column for a in anomalies if a.column}
    for col in sorted(columns):
        if re.search(rf"[\"']{re.escape(col)}[\"']", changed):
            signals.append(f"changed lines reference anomalous column '{col}'")
            score += 0.35

    removed_text = "\n".join(line.content for line in hunk.removed)
    added_text = "\n".join(line.content for line in hunk.added)
    for a in anomalies:
        value = a.details.get("value") if a.rule == "category_disappearance" else None
        if value and value in removed_text and value not in added_text:
            signals.append(f"value '{value}' removed from code and missing from data")
            score += 0.2

    matched_rules: set[str] = set()
    for a in anomalies:
        for pattern, label in RULE_PATTERNS.get(a.rule, []):
            if a.rule not in matched_rules and re.search(pattern, changed):
                signals.append(f"{label} change is consistent with {a.rule} anomaly")
                matched_rules.add(a.rule)
                score += 0.15

    first_changed = next((line for line in hunk.lines if line.kind == "+"), None) or next(
        (line for line in hunk.lines if line.kind == "-"), None
    )
    line_no = first_changed.new_lineno if first_changed and first_changed.new_lineno else hunk.new_start
    return SuspectChange(
        commit_sha=commit_sha,
        file=hunk.file,
        line=line_no,
        removed=[line.content for line in hunk.removed],
        added=[line.content for line in hunk.added],
        score=round(min(score, 1.0), 3),
        signals=signals,
    )


def _snippet(settings: Settings, file: str, line: int) -> SourceSnippet | None:
    try:
        path = resolve_in_repo(settings.pipeline_repo, file)
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return None
    start = max(1, line - SNIPPET_CONTEXT)
    end = min(len(lines), line + SNIPPET_CONTEXT)
    body = "\n".join(f"{n:>4} | {lines[n - 1]}" for n in range(start, end + 1))
    return SourceSnippet(file=file, start_line=start, end_line=end, content=body)


def build_evidence(
    settings: Settings,
    git: GitRepository,
    incident_id: str,
    detection: DetectionReport,
    baseline_profile: DatasetProfile,
    current_profile: DatasetProfile,
    baseline_run: PipelineRun,
    current_run: PipelineRun,
) -> EvidencePackage:
    recent = git.recent_commits(10)
    head = current_run.git_commit
    base = baseline_run.git_commit

    commit_evidence: list[CommitEvidence] = []
    if base and head and base != head:
        for info in git.commits_between(base, head):
            commit_evidence.append(git.commit_evidence(info.sha))
    elif not base:
        # No known-good commit: fall back to the last few commits.
        commit_evidence = [git.commit_evidence(c.sha) for c in recent[:3]]

    changed_files = sorted({f for ce in commit_evidence for f in ce.changed_files})

    suspects = [
        score_hunk(h, ce.commit.sha, detection.anomalies)
        for ce in commit_evidence
        for h in ce.hunks
    ]
    suspects.sort(key=lambda s: -s.score)

    snippets: list[SourceSnippet] = []
    seen: set[tuple[str, int]] = set()
    for s in suspects[:MAX_SNIPPETS]:
        if s.line and (s.file, s.line) not in seen:
            seen.add((s.file, s.line))
            snip = _snippet(settings, s.file, s.line)
            if snip:
                snippets.append(snip)

    disappeared: dict[str, list[str]] = {}
    for a in detection.anomalies:
        if a.rule == "category_disappearance" and a.column:
            disappeared.setdefault(a.column, []).append(a.details["value"])

    log.info(
        "Evidence for %s: %d commits since baseline, %d suspect hunks",
        incident_id, len(commit_evidence), len(suspects),
    )
    return EvidencePackage(
        incident_id=incident_id,
        anomaly_summary=detection.summary,
        anomalies=detection.anomalies,
        baseline_profile=baseline_profile,
        current_profile=current_profile,
        schema_differences=schema_diff(baseline_profile, current_profile),
        category_disappearance=disappeared,
        pipeline_run=current_run,
        baseline_run=baseline_run,
        logs=current_run.logs,
        baseline_commit=base,
        head_commit=head,
        recent_commits=recent,
        commits_since_baseline=commit_evidence,
        changed_files=changed_files,
        source_snippets=snippets,
        suspect_changes=suspects,
    )
