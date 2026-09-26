"""Root cause analysis over an evidence package.

Two engines share one output contract:

* ``heuristic``: deterministic reasoning over the evidence (default; used in
  tests and whenever no LLM is configured or the LLM call fails).
* ``llm``: an LLM provider reasons over the same evidence. Its answer is then
  *grounded*: any file/line/commit not present in the evidence is rejected.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.core.logging import get_logger
from app.core.models import (
    EvidencePackage,
    IncidentType,
    RootCauseAnalysis,
    Severity,
    SuspectChange,
)
from app.investigation.prompts import RCA_SYSTEM_PROMPT, build_rca_user_prompt
from app.llm.base import LLMError, LLMMessage, LLMProvider

log = get_logger("rca")

MIN_SUSPECT_SCORE = 0.3

# Anomaly rule -> incident type, in priority order.
RULE_TO_TYPE: list[tuple[str, IncidentType]] = [
    ("category_disappearance", IncidentType.FILTER_REGRESSION),
    ("schema", IncidentType.SCHEMA_DRIFT),
    ("null_rate", IncidentType.NULL_EXPLOSION),
    ("duplicates", IncidentType.DUPLICATE_INGESTION),
    ("numeric_drift", IncidentType.REVENUE_SHIFT),
]


def classify(evidence: EvidencePackage) -> IncidentType:
    rules = {a.rule for a in evidence.anomalies if a.severity != Severity.INFO}
    for rule, itype in RULE_TO_TYPE:
        if rule in rules:
            return itype
    rc = next((a for a in evidence.anomalies if a.rule == "row_count"), None)
    if rc and (rc.delta or 0) < 0:
        return IncidentType.FILTER_REGRESSION
    return IncidentType.UNKNOWN


def _overall_severity(evidence: EvidencePackage) -> Severity:
    return max((a.severity for a in evidence.anomalies), key=lambda s: s.rank, default=Severity.INFO)


def _human_join(items: list[str]) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _code(lines: list[str]) -> str:
    return " / ".join(line.strip() for line in lines if line.strip()) or "(nothing)"


def _commit_for(evidence: EvidencePackage, sha: str):
    return next((ce.commit for ce in evidence.commits_since_baseline if ce.commit.sha == sha), None)


def _impact(evidence: EvidencePackage, itype: IncidentType) -> str:
    base, cur = evidence.baseline_profile, evidence.current_profile
    parts: list[str] = []
    lost = base.row_count - cur.row_count
    if lost > 0:
        parts.append(f"{lost:,} of {base.row_count:,} rows ({lost / base.row_count:.1%}) are missing from the Gold output")
    elif lost < 0:
        parts.append(f"{-lost:,} extra rows ({-lost / base.row_count:.1%}) appeared in the Gold output")
    for col, values in evidence.category_disappearance.items():
        shares = base.columns[col].frequencies or {}
        share = sum(shares.get(v, 0.0) for v in values)
        parts.append(f"all {_human_join(values)} records ({share:.1%} of baseline '{col}') were excluded")
    rev_b, rev_c = base.columns.get("revenue"), cur.columns.get("revenue")
    if rev_b and rev_b.numeric and rev_c and rev_c.numeric:
        total_b = rev_b.numeric.mean * (base.row_count - rev_b.null_count)
        total_c = rev_c.numeric.mean * (cur.row_count - rev_c.null_count)
        if total_b and abs(total_c - total_b) / total_b >= 0.02:
            parts.append(f"reported revenue moved from {total_b:,.0f} to {total_c:,.0f} ({(total_c - total_b) / total_b:+.1%})")
    for a in evidence.anomalies:
        if a.rule in {"null_rate", "schema", "duplicates"} and a.severity == Severity.CRITICAL:
            parts.append(a.description.rstrip("."))
    if not parts:
        return "Downstream consumers receive data that deviates from the healthy baseline."
    return "; ".join(parts) + ". Downstream dashboards and reports built on this table are wrong while the pipeline reports SUCCESS."


def _mechanism(itype: IncidentType, evidence: EvidencePackage, top: SuspectChange) -> str:
    cols = sorted({a.column for a in evidence.anomalies if a.column})
    if itype == IncidentType.FILTER_REGRESSION:
        excluded = _human_join([v for vals in evidence.category_disappearance.values() for v in vals]) or "records"
        col = next(iter(evidence.category_disappearance), cols[0] if cols else "the filtered column")
        return (f"The row filter on '{col}' was narrowed, so {excluded} rows are dropped "
                f"in the transformation and never reach the Gold layer.")
    if itype == IncidentType.NULL_EXPLOSION:
        null_cols = [a.column for a in evidence.anomalies if a.rule == "null_rate"]
        return f"The new code masks values in {', '.join(null_cols)}, turning populated values into nulls."
    if itype == IncidentType.DUPLICATE_INGESTION:
        return "The new code appends a re-sampled copy of already-ingested records, creating duplicate rows."
    if itype == IncidentType.SCHEMA_DRIFT:
        sd = evidence.schema_differences
        return (f"The output schema changed (missing: {', '.join(sd.get('missing_columns', [])) or 'none'}; "
                f"new: {', '.join(sd.get('new_columns', [])) or 'none'}), breaking the downstream contract.")
    if itype == IncidentType.REVENUE_SHIFT:
        return "The new code rescales a numeric measure, shifting its whole distribution."
    return "The change is the strongest correlate of the observed anomalies."


def heuristic_rca(evidence: EvidencePackage, notes: list[str] | None = None) -> RootCauseAnalysis:
    itype = classify(evidence)
    severity = _overall_severity(evidence)
    suspects = evidence.suspect_changes
    top = suspects[0] if suspects else None
    notes = list(notes or [])

    facts = [
        f"Pipeline run {evidence.pipeline_run.run_id} finished with status {evidence.pipeline_run.status.value}.",
        f"Gold rows: baseline {evidence.baseline_profile.row_count:,} -> current {evidence.current_profile.row_count:,}.",
    ]
    facts += [f"{a.severity.value}: {a.description}" for a in evidence.anomalies if a.severity != Severity.INFO][:6]
    if evidence.baseline_commit and evidence.head_commit:
        facts.append(
            f"{len(evidence.commits_since_baseline)} commit(s) between baseline commit "
            f"{evidence.baseline_commit[:7]} and current commit {evidence.head_commit[:7]}."
        )

    if top is None or top.score < MIN_SUSPECT_SCORE:
        return RootCauseAnalysis(
            incident_type=itype,
            severity=severity,
            likely_root_cause=(
                "Insufficient evidence: no code change since the last healthy run correlates with the "
                "observed anomalies. The cause may be upstream data rather than pipeline code."
            ),
            file=None, line=None, commit=None,
            confidence=0.2,
            impact=_impact(evidence, itype),
            recommended_fix="Investigate upstream source data and recent configuration changes; no safe code fix can be proposed.",
            observed_facts=facts,
            inferences=["No diff hunk matched the anomalous columns or anomaly patterns."],
            insufficient_evidence=True,
            engine="heuristic",
            engine_notes=notes,
        )

    commit = _commit_for(evidence, top.commit_sha)
    short = top.commit_sha[:7]
    msg = commit.message if commit else ""
    facts.append(f"Commit {short} (\"{msg}\") changed {top.file} line {top.line}: "
                 f"`{_code(top.removed)}` -> `{_code(top.added)}`.")

    runner_up = suspects[1].score if len(suspects) > 1 else 0.0
    single_commit = len(evidence.commits_since_baseline) == 1
    confidence = 0.35 + 0.45 * top.score + (0.08 if single_commit else 0.0) + (0.07 if top.score - runner_up >= 0.2 else 0.0)
    confidence = round(min(confidence, 0.95), 2)

    inferences = [f"Correlation signal: {s}." for s in top.signals]
    inferences.append(_mechanism(itype, evidence, top))
    if single_commit:
        inferences.append("It is the only code change since the last healthy baseline run.")

    if top.removed:
        fix = f"Restore the previous code at {top.file}:{top.line}: `{_code(top.removed)}` (revert the change from commit {short})."
    else:
        fix = f"Remove the line(s) introduced by commit {short} at {top.file}:{top.line}: `{_code(top.added)}`."

    cause = (
        f"Commit {short} (\"{msg}\") changed {top.file} line {top.line} from `{_code(top.removed)}` "
        f"to `{_code(top.added)}`. {_mechanism(itype, evidence, top)}"
    )
    return RootCauseAnalysis(
        incident_type=itype,
        severity=severity,
        likely_root_cause=cause,
        file=top.file,
        line=top.line,
        commit=top.commit_sha,
        commit_message=msg or None,
        confidence=confidence,
        impact=_impact(evidence, itype),
        recommended_fix=fix,
        observed_facts=facts,
        inferences=inferences,
        engine="heuristic",
        engine_notes=notes,
    )


# ------------------------------------------------------------------ LLM path


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise LLMError("Model response contained no JSON object")
    try:
        result = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model returned invalid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise LLMError("Model response must be a JSON object")
    return result


def _valid_lines(evidence: EvidencePackage, file: str) -> set[int]:
    lines: set[int] = set()
    for ce in evidence.commits_since_baseline:
        for h in ce.hunks:
            if h.file == file:
                lines |= {line.new_lineno for line in h.lines if line.new_lineno}
    for s in evidence.source_snippets:
        if s.file == file:
            lines |= set(range(s.start_line, s.end_line + 1))
    return lines


def ground_llm_result(raw: dict, evidence: EvidencePackage, fallback: RootCauseAnalysis, label: str) -> RootCauseAnalysis:
    """Reject any repository facts that are not present in the evidence."""
    notes: list[str] = []
    known_files = set(evidence.changed_files) | {s.file for s in evidence.source_snippets}
    known_commits = [ce.commit.sha for ce in evidence.commits_since_baseline]

    file = raw.get("file")
    if file and file not in known_files:
        notes.append(f"LLM cited file '{file}' which is not in the evidence; replaced with deterministic finding.")
        file = fallback.file

    line = raw.get("line")
    try:
        line = int(line) if line is not None else None
    except (TypeError, ValueError):
        line = None
    if file and line is not None and line not in _valid_lines(evidence, file):
        notes.append(f"LLM cited line {line} which is not in the diff/snippets; replaced with deterministic finding.")
        line = fallback.line if file == fallback.file else None

    commit = raw.get("commit")
    if commit:
        match = next((sha for sha in known_commits if sha.startswith(str(commit))), None)
        if match is None:
            notes.append(f"LLM cited commit '{commit}' which is not in the evidence; replaced with deterministic finding.")
        commit = match or fallback.commit
    if file and commit and not any(
        ce.commit.sha == commit and any(h.file == file for h in ce.hunks)
        for ce in evidence.commits_since_baseline
    ):
        notes.append("LLM cited a file and commit that do not belong to the same change; replaced with deterministic finding.")
        file, line, commit = fallback.file, fallback.line, fallback.commit
    commit_info = _commit_for(evidence, commit) if commit else None

    try:
        confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0

    # Inferences are the only explanatory field taken from the LLM.
    # Apply strict length and count limits to bound prompt-injection surface.
    _MAX_INFERENCE_ITEMS = 10
    _MAX_INFERENCE_LEN = 500
    raw_inferences = raw.get("inferences")
    if isinstance(raw_inferences, list):
        inferences = [
            str(x)[:_MAX_INFERENCE_LEN]
            for x in raw_inferences
            if isinstance(x, str)
        ][:_MAX_INFERENCE_ITEMS]
        if not inferences:
            inferences = fallback.inferences
    else:
        inferences = fallback.inferences

    return RootCauseAnalysis(
        incident_type=fallback.incident_type,
        severity=fallback.severity,
        # Consequential operator-facing text always comes from the deterministic
        # heuristic result, never from raw LLM output.
        likely_root_cause=fallback.likely_root_cause,
        file=file,
        line=line,
        commit=commit,
        commit_message=commit_info.message if commit_info else None,
        confidence=round(confidence, 2),
        impact=fallback.impact,
        recommended_fix=fallback.recommended_fix,
        observed_facts=fallback.observed_facts,
        inferences=inferences,
        insufficient_evidence=fallback.insufficient_evidence,
        engine=f"llm:{label}",
        engine_notes=notes,
    )


def run_rca(evidence: EvidencePackage, provider: LLMProvider | None) -> RootCauseAnalysis:
    baseline = heuristic_rca(evidence)
    if provider is None:
        return baseline
    try:
        text = provider.generate(RCA_SYSTEM_PROMPT, [LLMMessage(role="user", content=build_rca_user_prompt(evidence))])
        result = ground_llm_result(_extract_json(text), evidence, baseline, provider.label)
        log.info("LLM RCA (%s) confidence=%.2f", provider.label, result.confidence)
        return result
    except (LLMError, ValidationError, KeyError, TypeError) as exc:
        log.warning("LLM RCA failed, falling back to heuristic: %s", exc)
        return heuristic_rca(evidence, notes=[f"LLM ({provider.label}) unavailable: {exc}. Deterministic analysis used."])
