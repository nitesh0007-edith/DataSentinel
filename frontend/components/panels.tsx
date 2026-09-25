"use client";

import { useState } from "react";
import type { DashboardState, Incident, PipelineRun, DetectionReport, TimelineEvent } from "@/types";
import { fmtInt, fmtPct, fmtTime, titleCase } from "@/lib/format";
import { Empty, Pill, StatusIcon, toneFor } from "./ui";

/* ------------------------------------------------------------------ hero: the core contrast */

const HERO_TONE = {
  good: "border-good/40 bg-good-soft text-good-ink",
  warning: "border-warning/50 bg-warning-soft text-warning-ink",
  critical: "border-critical/50 bg-critical-soft text-critical-ink",
  neutral: "border-line bg-surface text-ink-2",
  info: "border-line bg-surface text-ink-2",
} as const;

function HeroTile({ label, value, sub, tone, pulse }: { label: string; value: string; sub: string; tone: keyof typeof HERO_TONE; pulse?: boolean }) {
  return (
    <div className={`flex-1 rounded-xl border-2 px-6 py-5 ${HERO_TONE[tone]}`}>
      <div className="text-xs font-semibold uppercase tracking-widest opacity-80">{label}</div>
      <div className={`mt-1 flex items-center gap-3 text-4xl font-bold tracking-tight md:text-5xl ${pulse ? "ds-pulse" : ""}`}>
        <StatusIcon tone={tone} className="h-9 w-9" />
        {value}
      </div>
      <div className="mt-2 text-sm text-ink-2">{sub}</div>
    </div>
  );
}

export function StatusHero({ run, detection }: { run: PipelineRun | null; detection: DetectionReport | null }) {
  const health = run ? (detection && detection.run_id === run.run_id ? detection.data_health : run.data_health) : "UNKNOWN";
  const healthTone = health === "UNKNOWN" ? "neutral" : toneFor(health);
  const contrast = run?.status === "SUCCESS" && (health === "CRITICAL" || health === "WARNING");
  return (
    <div>
      <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
        <HeroTile
          label="Pipeline status (orchestrator)"
          value={run?.status ?? "NO RUNS"}
          tone={run ? toneFor(run.status) : "neutral"}
          sub={run ? `${run.run_id} · ${fmtInt(run.rows_input)} → ${fmtInt(run.rows_output)} rows · ${Math.round(run.duration_ms)} ms` : "Run the pipeline to begin."}
        />
        <div className="hidden items-center text-2xl font-light text-ink-3 md:flex">vs</div>
        <HeroTile
          label="Data health (DataSentinel)"
          value={health === "UNKNOWN" ? "NOT CHECKED" : health}
          tone={healthTone}
          pulse={health === "CRITICAL"}
          sub={
            health === "UNKNOWN"
              ? "Click Detect to check this run against the healthy baseline."
              : detection?.summary ?? ""
          }
        />
      </div>
      {contrast && (
        <p className="mt-3 flex items-center gap-2 rounded-lg bg-critical-soft px-4 py-2 text-sm font-medium text-critical-ink">
          <StatusIcon tone="critical" /> Silent data failure: the orchestrator reports SUCCESS, but the output data is wrong.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ KPI row */

function Kpi({ label, value, delta, tone, hint }: { label: string; value: string; delta?: string; tone?: "good" | "critical" | "warning" | "neutral"; hint?: string }) {
  const ink = { good: "text-good-ink", critical: "text-critical-ink", warning: "text-warning-ink", neutral: "text-ink-2" }[tone ?? "neutral"];
  return (
    <div className="rounded-xl border border-line bg-surface px-4 py-3">
      <div className="text-xs text-ink-3">{label}</div>
      <div className="tabular mt-1 text-2xl font-semibold text-ink">{value}</div>
      {delta && (
        <div className={`mt-0.5 flex items-center gap-1 text-xs font-medium ${ink}`}>
          {tone && tone !== "neutral" && <StatusIcon tone={tone} className="h-3 w-3" />}
          {delta}
        </div>
      )}
      {hint && <div className="mt-0.5 text-xs text-ink-3">{hint}</div>}
    </div>
  );
}

export function KpiRow({ state }: { state: DashboardState }) {
  const b = state.baseline_profile;
  const c = state.latest_profile;
  const det = state.last_detection && state.latest_run && state.last_detection.run_id === state.latest_run.run_id ? state.last_detection : null;
  const rowChange = b && c ? (c.row_count - b.row_count) / b.row_count : null;
  const nullPct = (p: typeof b) =>
    p ? Object.values(p.columns).reduce((s, col) => s + col.null_count, 0) / Math.max(1, p.row_count * p.column_count) : null;
  const nb = nullPct(b), nc = nullPct(c);
  const schemaIssues = det?.anomalies.filter((a) => a.rule === "schema").length ?? 0;
  const sev = state.active_incident && state.active_incident.status !== "RESOLVED" ? state.active_incident.severity : null;

  const rowTone = rowChange == null ? "neutral" : Math.abs(rowChange) >= 0.25 ? "critical" : Math.abs(rowChange) >= 0.1 ? "warning" : "good";
  const nullTone = nb == null || nc == null ? "neutral" : nc - nb >= 0.05 ? "critical" : "good";
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      <Kpi label="Gold rows" value={fmtInt(c?.row_count)} delta={rowChange == null ? undefined : `${fmtPct(rowChange, 1, true)} vs baseline`} tone={rowTone} hint={b ? `Baseline ${fmtInt(b.row_count)}` : undefined} />
      <Kpi label="Null rate (all cells)" value={fmtPct(nc, 2)} delta={nb == null || nc == null ? undefined : `${((nc - nb) * 100).toFixed(2)} pp vs baseline`} tone={nullTone} />
      <Kpi label="Duplicate rows" value={fmtPct(c?.duplicate_pct, 2)} hint={c ? `${fmtInt(c.duplicate_count)} rows` : undefined} delta={b && c ? `${((c.duplicate_pct - b.duplicate_pct) * 100).toFixed(2)} pp vs baseline` : undefined} tone={b && c ? (c.duplicate_pct - b.duplicate_pct >= 0.01 ? "critical" : "good") : "neutral"} />
      <Kpi label="Schema" value={c ? `${c.column_count} cols` : "—"} delta={det ? (schemaIssues ? `${schemaIssues} schema change(s)` : "Matches baseline") : undefined} tone={det ? (schemaIssues ? "critical" : "good") : "neutral"} />
      <div className="col-span-2 rounded-xl border border-line bg-surface px-4 py-3 lg:col-span-1">
        <div className="text-xs text-ink-3">Incident severity</div>
        <div className="mt-2">{sev ? <Pill value={sev} /> : <Pill tone="good" label="No open incident" />}</div>
        {state.active_incident && <div className="mt-1.5 text-xs text-ink-3">{state.active_incident.id} · {titleCase(state.active_incident.status)}</div>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ anomalies */

export function AnomalyList({ detection }: { detection: DetectionReport | null }) {
  if (!detection) return <Empty>No detection run for the latest pipeline run.</Empty>;
  if (!detection.anomalies.length)
    return (
      <p className="flex items-center gap-2 rounded-lg bg-good-soft px-4 py-3 text-sm font-medium text-good-ink">
        <StatusIcon tone="good" /> No anomalies against baseline {detection.baseline_run_id}.
      </p>
    );
  return (
    <ul className="divide-y divide-line">
      {detection.anomalies.map((a) => (
        <li key={a.id} className="flex items-start gap-3 py-2.5">
          <Pill value={a.severity} />
          <div className="min-w-0">
            <div className="text-sm font-medium text-ink">{a.title}</div>
            <div className="text-xs text-ink-2">{a.description}</div>
          </div>
          <span className="ml-auto shrink-0 rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-ink-3">{a.rule}</span>
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ investigation */

const STEP_PLAN = [
  { key: "data", label: "Data evidence" },
  { key: "git", label: "Git history" },
  { key: "correlate", label: "Change correlation" },
  { key: "rca", label: "Root cause analysis" },
];

export function InvestigationProgress({ incident, running }: { incident: Incident | null; running: boolean }) {
  const steps = incident?.investigation_steps ?? [];
  return (
    <ol className="space-y-2.5">
      {STEP_PLAN.map((p, i) => {
        const s = steps.find((x) => x.key === p.key);
        const tone = s ? (s.status === "done" ? "good" : s.status === "failed" ? "critical" : "neutral") : "neutral";
        return (
          <li key={p.key} className="flex gap-3">
            <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${s ? (tone === "good" ? "bg-good-soft text-good-ink" : tone === "critical" ? "bg-critical-soft text-critical-ink" : "bg-surface-2 text-ink-3") : "bg-surface-2 text-ink-3"}`}>
              {running && !s ? <span className="ds-pulse">•</span> : s ? <StatusIcon tone={tone} className="h-4 w-4" /> : i + 1}
            </span>
            <div className="min-w-0">
              <div className="text-sm font-medium text-ink">
                {p.label}
                {s && s.duration_ms > 0 && <span className="tabular ml-2 text-xs font-normal text-ink-3">{s.duration_ms.toFixed(0)} ms</span>}
              </div>
              <div className="text-xs text-ink-2">{s ? s.detail : running ? "Running…" : "Pending"}</div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function EvidencePanel({ incident }: { incident: Incident | null }) {
  const ev = incident?.evidence;
  if (!ev) return <Empty>Evidence appears after Investigate.</Empty>;
  const top = ev.suspect_changes[0];
  return (
    <div className="space-y-4 text-sm">
      <div>
        <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-3">Commits since last healthy baseline</div>
        {ev.commits_since_baseline.length === 0 && <div className="text-ink-3">None</div>}
        {ev.commits_since_baseline.map((ce) => (
          <div key={ce.commit.sha} className="rounded-lg bg-surface-2 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <code className="rounded bg-surface px-1.5 font-mono text-xs text-accent">{ce.commit.short_sha}</code>
              <span className="font-medium text-ink">{ce.commit.message}</span>
            </div>
            <div className="mt-0.5 text-xs text-ink-3">{ce.commit.author} · {ce.changed_files.join(", ")}</div>
          </div>
        ))}
      </div>
      {top && (
        <div>
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-3">
            Correlation signals · <span className="font-mono normal-case">{top.file}:{top.line}</span> · score {top.score.toFixed(2)}
          </div>
          <ul className="space-y-1">
            {top.signals.map((s) => (
              <li key={s} className="flex items-start gap-2 text-xs text-ink-2">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" /> {s}
              </li>
            ))}
          </ul>
        </div>
      )}
      {ev.source_snippets[0] && (
        <div>
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-3">Source at failing commit</div>
          <pre className="overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-[11px] leading-5 text-ink-2">
            {ev.source_snippets[0].content.split("\n").map((l) => {
              const n = parseInt(l, 10);
              const hit = incident?.rca?.line === n;
              return (
                <div key={l} className={hit ? "-mx-3 bg-critical-soft px-3 font-semibold text-critical-ink" : ""}>{l}</div>
              );
            })}
          </pre>
        </div>
      )}
    </div>
  );
}

export function RootCauseCard({ incident }: { incident: Incident | null }) {
  const [showFacts, setShowFacts] = useState(false);
  const rca = incident?.rca;
  if (!rca) return <Empty>Root cause appears after Investigate.</Empty>;
  const pct = Math.round(rca.confidence * 100);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Pill value={rca.severity} />
        <span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-semibold text-ink">{titleCase(rca.incident_type)}</span>
        <span className="rounded-full bg-surface-2 px-2.5 py-0.5 font-mono text-[11px] text-ink-3">engine: {rca.engine}</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
        <div>
          <div className="text-xs text-ink-3">Impacted file</div>
          <div className="font-mono text-sm font-semibold text-ink">
            {rca.file ?? "—"}
            {rca.line ? <span className="text-critical-ink"> : line {rca.line}</span> : null}
          </div>
          {rca.commit && (
            <div className="mt-1 text-xs text-ink-2">
              commit <code className="font-mono text-accent">{rca.commit.slice(0, 7)}</code> {rca.commit_message && `“${rca.commit_message}”`}
            </div>
          )}
        </div>
        <div className="min-w-36">
          <div className="text-xs text-ink-3">Confidence</div>
          <div className="tabular text-3xl font-bold text-ink">{pct}%</div>
          <div className="mt-1 h-1.5 w-full rounded-full bg-surface-2">
            <div className="h-full rounded-full bg-accent transition-[width] duration-700" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
      <p className="text-sm leading-relaxed text-ink">{rca.likely_root_cause}</p>
      <div className="rounded-lg bg-surface-2 px-3 py-2 text-sm">
        <div className="text-xs font-semibold text-ink-3">Impact</div>
        <div className="text-ink-2">{rca.impact}</div>
      </div>
      <div className="rounded-lg bg-surface-2 px-3 py-2 text-sm">
        <div className="text-xs font-semibold text-ink-3">Recommended fix</div>
        <div className="text-ink-2">{rca.recommended_fix}</div>
      </div>
      {rca.engine_notes.length > 0 && (
        <ul className="text-xs text-warning-ink">{rca.engine_notes.map((n) => <li key={n}>• {n}</li>)}</ul>
      )}
      <button className="text-xs text-accent hover:underline" onClick={() => setShowFacts((v) => !v)}>
        {showFacts ? "Hide" : "Show"} observed facts vs inferences
      </button>
      {showFacts && (
        <div className="grid gap-3 text-xs md:grid-cols-2">
          <div>
            <div className="mb-1 font-semibold text-ink">Observed facts</div>
            <ul className="space-y-1 text-ink-2">{rca.observed_facts.map((f) => <li key={f}>• {f}</li>)}</ul>
          </div>
          <div>
            <div className="mb-1 font-semibold text-ink">Inferences</div>
            <ul className="space-y-1 text-ink-2">{rca.inferences.map((f) => <li key={f}>• {f}</li>)}</ul>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ diff */

export function DiffView({ diff }: { diff: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg border border-line bg-surface-2 py-2 font-mono text-[12px] leading-5">
      {diff.split("\n").map((line, i) => {
        const cls = line.startsWith("+++") || line.startsWith("---")
          ? "text-ink-3"
          : line.startsWith("+")
            ? "bg-[var(--diff-add)] text-good-ink"
            : line.startsWith("-")
              ? "bg-[var(--diff-del)] text-critical-ink"
              : line.startsWith("@@")
                ? "text-accent"
                : "text-ink-2";
        return <div key={i} className={`px-3 ${cls}`}>{line || " "}</div>;
      })}
    </pre>
  );
}

export function GitDiffPanel({ incident }: { incident: Incident | null }) {
  const ce = incident?.evidence?.commits_since_baseline.find((c) => c.commit.sha === incident?.rca?.commit) ?? incident?.evidence?.commits_since_baseline[0];
  if (!ce) return <Empty>The offending diff appears after Investigate.</Empty>;
  return (
    <div>
      <div className="mb-2 text-xs text-ink-3">
        <code className="font-mono text-accent">{ce.commit.short_sha}</code> {ce.commit.message} — {ce.commit.author}
      </div>
      <DiffView diff={ce.diff.trim()} />
    </div>
  );
}

export function RemediationPanel({ incident }: { incident: Incident | null }) {
  const p = incident?.patch;
  if (!p) return <Empty>Click Generate Fix to propose a patch. Nothing is changed until you approve it.</Empty>;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Pill value={p.status} />
        <span className="font-mono text-xs text-ink-3">{p.patch_id}</span>
        {p.applied_commit && <span className="text-xs text-ink-2">committed as <code className="font-mono text-accent">{p.applied_commit.slice(0, 7)}</code></span>}
      </div>
      <p className="text-sm text-ink-2">{p.description}</p>
      <DiffView diff={p.diff.trim()} />
    </div>
  );
}

/* ------------------------------------------------------------------ validation */

export function ValidationPanel({ incident }: { incident: Incident | null }) {
  const v = incident?.validation;
  if (!v) return <Empty>Validation reruns the pipeline, re-profiles the output, compares to baseline and runs the repository tests.</Empty>;
  return (
    <div className="space-y-3">
      <ul className="space-y-1.5">
        {v.checks.map((c) => (
          <li key={c.name} className="flex items-start gap-2 text-sm">
            <span className={c.passed ? "text-good-ink" : "text-critical-ink"}>
              <StatusIcon tone={c.passed ? "good" : "critical"} className="mt-0.5 h-4 w-4" />
            </span>
            <div>
              <span className="font-medium text-ink">{c.name}</span>
              <span className="ml-2 text-xs text-ink-3">{c.detail}</span>
            </div>
          </li>
        ))}
      </ul>
      <div className={`flex items-center gap-2 rounded-lg px-4 py-3 text-lg font-bold ${v.passed ? "bg-good-soft text-good-ink" : "bg-critical-soft text-critical-ink"}`}>
        <StatusIcon tone={v.passed ? "good" : "critical"} className="h-5 w-5" />
        {v.passed ? `INCIDENT ${incident?.id} RESOLVED` : "VALIDATION FAILED — incident remains open"}
        <span className="ml-auto text-xs font-normal">validation run {v.run_id}</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ events + report */

export function EventLog({ events }: { events: TimelineEvent[] }) {
  if (!events.length) return <Empty>No activity yet.</Empty>;
  return (
    <ul className="max-h-80 space-y-2 overflow-y-auto pr-1">
      {events.map((e, i) => (
        <li key={`${e.timestamp}-${i}`} className="flex gap-3 text-xs">
          <span className="tabular shrink-0 text-ink-3">{fmtTime(e.timestamp)}</span>
          <span className={`shrink-0 font-semibold uppercase ${e.severity === "CRITICAL" ? "text-critical-ink" : e.kind === "resolved" ? "text-good-ink" : "text-ink-2"}`}>{e.kind}</span>
          <span className="text-ink-2">{e.message}</span>
        </li>
      ))}
    </ul>
  );
}

export function ReportViewer({ markdown, path }: { markdown: string | null; path: string | null | undefined }) {
  if (!markdown) return <Empty>The incident report is generated as Markdown under artifacts/incidents/.</Empty>;
  return (
    <div>
      {path && <div className="mb-2 font-mono text-xs text-ink-3">{path}</div>}
      <pre className="max-h-[480px] overflow-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-4 font-mono text-[12px] leading-5 text-ink-2">{markdown}</pre>
    </div>
  );
}

