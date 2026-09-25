"""Markdown incident report generation."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.core.models import Incident
from app.core.state import write_text_atomic


def render_report(incident: Incident) -> str:
    d = incident.detection
    rca = incident.rca
    patch = incident.patch
    val = incident.validation
    ev = incident.evidence
    out: list[str] = []
    w = out.append

    w(f"# Incident {incident.id}: {rca.incident_type.value.replace('_', ' ').title() if rca else 'Data incident'}\n")
    w("| Field | Value |\n|---|---|")
    w(f"| Incident ID | `{incident.id}` |")
    w(f"| Detected | {incident.created_at:%Y-%m-%d %H:%M:%S UTC} |")
    w(f"| Severity | **{incident.severity.value}** |")
    w(f"| Final status | **{incident.status.value}** |")
    if incident.resolved_at:
        w(f"| Resolved | {incident.resolved_at:%Y-%m-%d %H:%M:%S UTC} |")
    w(f"| Affected run | `{incident.run_id}` (pipeline status: {ev.pipeline_run.status.value if ev else 'SUCCESS'}) |")
    w(f"| Baseline run | `{incident.baseline_run_id}` |")
    if rca:
        w(f"| RCA engine | {rca.engine} |")
    w("")

    w("## Symptoms\n")
    w(f"The pipeline reported **SUCCESS**, but data health was **{d.data_health.value}**.\n")
    w(f"- Rows: {d.row_count_baseline:,} (baseline) → {d.row_count_current:,} (current), {d.row_count_change_pct:+.1%}")
    w(f"- {d.summary}\n")

    w("## Detected anomalies\n")
    w("| Severity | Rule | Anomaly | Detail |\n|---|---|---|---|")
    for a in d.anomalies:
        w(f"| {a.severity.value} | {a.rule} | {a.title} | {a.description} |")
    w("")

    if ev:
        w("## Evidence\n")
        w(f"- Baseline commit: `{(ev.baseline_commit or 'n/a')[:7]}`; commit at failing run: `{(ev.head_commit or 'n/a')[:7]}`")
        w(f"- Commits since baseline: {len(ev.commits_since_baseline)}")
        for ce in ev.commits_since_baseline:
            w(f"  - `{ce.commit.short_sha}` {ce.commit.message} ({ce.commit.author}); files: {', '.join(ce.changed_files)}")
        if ev.suspect_changes:
            top = ev.suspect_changes[0]
            w(f"- Strongest correlated change: `{top.file}:{top.line}` (score {top.score:.2f})")
            for s in top.signals:
                w(f"  - {s}")
        w("")

    w("## Root cause\n")
    if rca:
        w(f"{rca.likely_root_cause}\n")
        w(f"- **Impacted file:** `{rca.file or 'n/a'}`" + (f" line {rca.line}" if rca.line else ""))
        w(f"- **Commit:** `{(rca.commit or 'n/a')[:7]}`" + (f" — {rca.commit_message}" if rca.commit_message else ""))
        w(f"- **Confidence:** {rca.confidence:.0%}")
        w(f"- **Impact:** {rca.impact}\n")
        if rca.observed_facts:
            w("**Observed facts**\n")
            out.extend(f"- {f}" for f in rca.observed_facts)
            w("")
        if rca.inferences:
            w("**Inferences**\n")
            out.extend(f"- {i}" for i in rca.inferences)
            w("")
        if rca.engine_notes:
            w("**Engine notes**\n")
            out.extend(f"- {n}" for n in rca.engine_notes)
            w("")
    else:
        w("Not investigated.\n")

    w("## Remediation\n")
    if patch:
        w(f"Status: **{patch.status}**" + (f" (commit `{patch.applied_commit[:7]}`)" if patch.applied_commit else "") + "\n")
        w(f"{patch.description}\n")
        w("```diff\n" + patch.diff.rstrip() + "\n```\n")
    else:
        w("No patch proposed.\n")

    w("## Validation\n")
    if val:
        for c in val.checks:
            w(f"- {'✅' if c.passed else '❌'} **{c.name}**: {c.detail}")
        w(f"\nValidation run: `{val.run_id}`. Result: **{'PASSED' if val.passed else 'FAILED'}**\n")
    else:
        w("Not validated.\n")

    w(f"## Final status\n\n**{incident.status.value}**\n")
    return "\n".join(out)


def write_report(settings: Settings, incident: Incident) -> Path:
    path = settings.incidents_dir / f"{incident.id}.md"
    write_text_atomic(path, render_report(incident))
    return path
