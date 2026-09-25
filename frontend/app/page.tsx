"use client";

import { useCallback, useEffect, useState } from "react";
import { api, API_URL } from "@/lib/api";
import type { DashboardState } from "@/types";
import { ACTION_LABELS, ControlBar, nextAction, type ActionKey } from "@/components/ControlBar";
import { CategoryComparison, RunTimeline } from "@/components/charts";
import {
  AnomalyList,
  EventLog,
  EvidencePanel,
  GitDiffPanel,
  InvestigationProgress,
  KpiRow,
  RemediationPanel,
  ReportViewer,
  RootCauseCard,
  StatusHero,
  ValidationPanel,
} from "@/components/panels";
import { Card, Pill, StatusIcon } from "@/components/ui";

const NEXT_HINT: Record<ActionKey, string> = {
  reset: "Start by resetting the demo: rebuilds the monitored pipeline repo and generates deterministic data.",
  healthy: "Run the healthy pipeline to capture the known-good baseline profile.",
  inject: "Inject an incident: commits a realistic code regression to the pipeline repo.",
  run: "Run the pipeline. Watch the orchestrator report SUCCESS.",
  detect: "Ask DataSentinel to check the latest run against the healthy baseline.",
  investigate: "Investigate: collect data + Git evidence and identify the root cause.",
  fix: "Generate a proposed fix. Nothing is changed until you approve it.",
  reject: "",
  apply: "Review the diff, then apply the fix (committed to the pipeline repo).",
  validate: "Validate: rerun the pipeline, re-profile, compare with baseline and run repo tests.",
};

export default function Dashboard() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [busy, setBusy] = useState<ActionKey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [incidentType, setIncidentType] = useState("filter_regression");
  const [report, setReport] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await api.state();
      setState(s);
      setApiUp(true);
      return s;
    } catch (e) {
      setApiUp(false);
      setError((e as Error).message);
      return null;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const incident = state?.active_incident ?? null;

  useEffect(() => {
    if (!incident) {
      setReport(null);
      return;
    }
    api.report(incident.id).then(setReport).catch(() => setReport(null));
  }, [incident?.id, incident?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (key: ActionKey) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      const id = incident?.id ?? "";
      switch (key) {
        case "reset":
          await api.reset();
          setNotice("Demo reset: pipeline repo rebuilt and synthetic data regenerated.");
          break;
        case "healthy":
          await api.runPipeline(true);
          setNotice("Healthy baseline captured.");
          break;
        case "inject": {
          const r = (await api.inject(incidentType)) as { commit: string; commit_message: string };
          setNotice(`Committed ${r.commit.slice(0, 7)} “${r.commit_message}” to the pipeline repo.`);
          break;
        }
        case "run":
          await api.runPipeline(false);
          break;
        case "detect": {
          const r = (await api.detect()) as { incident: { id: string } | null; detection: { data_health: string } };
          setNotice(r.incident ? `${r.incident.id} opened: data health ${r.detection.data_health}.` : `Data health ${r.detection.data_health}. No incident.`);
          break;
        }
        case "investigate":
          await api.investigate(id);
          break;
        case "fix":
          await api.fix(id);
          break;
        case "reject":
          await api.reject(id);
          break;
        case "apply":
          await api.apply(id);
          break;
        case "validate":
          await api.validate(id);
          break;
      }
      await refresh();
    } catch (e) {
      setError(`${ACTION_LABELS[key]} failed: ${(e as Error).message}`);
      await refresh();
    } finally {
      setBusy(null);
    }
  };

  const next = nextAction(state);
  const baselineRun = state?.runs.find((r) => r.run_id === state.baseline_run_id);
  const detectionForLatest =
    state?.last_detection && state.latest_run && state.last_detection.run_id === state.latest_run.run_id ? state.last_detection : null;

  return (
    <main className="mx-auto max-w-[1400px] px-4 pb-16 pt-6 md:px-8">
      {/* header */}
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-white">
            <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden>
              <path d="M12 2l8 3v6c0 5-3.4 9.4-8 11-4.6-1.6-8-6-8-11V5z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
              <path d="M8 12.5l2.6 2.6L16 9.7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-ink">DataSentinel</h1>
            <p className="text-xs text-ink-3">Autonomous Data Reliability Engineer</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full border border-line bg-surface px-2.5 py-1 text-ink-2">
            Pipeline: <span className="font-medium text-ink">customer-revenue</span>
          </span>
          {state?.repository.head && (
            <span className="rounded-full border border-line bg-surface px-2.5 py-1 text-ink-2">
              HEAD <code className="font-mono text-accent">{state.repository.head.slice(0, 7)}</code>
            </span>
          )}
          {state && (
            <span className="rounded-full border border-line bg-surface px-2.5 py-1 text-ink-2">
              RCA engine: <span className="font-mono text-ink">{state.rca_engine}</span>
            </span>
          )}
          <Pill tone={apiUp ? "good" : apiUp === false ? "critical" : "neutral"} label={apiUp ? "API connected" : apiUp === false ? "API offline" : "Connecting"} />
        </div>
      </header>

      {/* controls */}
      <Card className="mb-5">
        <ControlBar state={state} busy={busy} onAction={run} incidentType={incidentType} setIncidentType={setIncidentType} />
        {next && !busy && NEXT_HINT[next] && (
          <p className="mt-3 text-xs text-ink-2">
            <span className="font-semibold text-accent">Next:</span> {NEXT_HINT[next]}
          </p>
        )}
        {busy && <p className="mt-3 text-xs text-ink-2">{ACTION_LABELS[busy]} in progress…</p>}
        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-critical-soft px-3 py-2 text-sm text-critical-ink" role="alert">
            <StatusIcon tone="critical" className="mt-0.5 h-4 w-4" />
            <span>{error}</span>
            {apiUp === false && <span className="ml-auto text-xs">Start the API: <code className="font-mono">uvicorn app.main:app --port 8000</code> ({API_URL})</span>}
          </div>
        )}
        {notice && !error && <p className="mt-3 text-xs text-ink-2">{notice}</p>}
      </Card>

      {state && (
        <div className="space-y-5">
          <StatusHero run={state.latest_run} detection={detectionForLatest} />
          <KpiRow state={state} />

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Country distribution" subtitle="Gold rows per country: healthy baseline vs latest run">
              <CategoryComparison baseline={state.baseline_profile} current={state.latest_profile} column="country" />
            </Card>
            <Card title="Pipeline runs" subtitle="Rows output per run, coloured by DataSentinel data health">
              <RunTimeline runs={state.runs} baselineRows={baselineRun?.rows_output ?? null} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-[3fr_2fr]">
            <Card title="Detected anomalies" subtitle={detectionForLatest ? `${state.latest_run?.run_id} vs baseline ${detectionForLatest.baseline_run_id}` : "Deterministic rules: row count, nulls, schema, duplicates, categories, distributions"}>
              <AnomalyList detection={detectionForLatest} />
            </Card>
            <Card title="Investigation" subtitle={incident ? `${incident.id} · ${incident.status.replace(/_/g, " ")}` : "Starts when an incident is open"}>
              <InvestigationProgress incident={incident} running={busy === "investigate"} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Root cause" subtitle="Evidence-grounded analysis from the backend investigation">
              <RootCauseCard incident={incident} />
            </Card>
            <Card title="Evidence" subtitle="Git history and correlation signals supplied to the RCA engine">
              <EvidencePanel incident={incident} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Offending change (git show)" subtitle="Commit implicated by the root cause analysis">
              <GitDiffPanel incident={incident} />
            </Card>
            <Card title="Suggested remediation" subtitle="View fix → Apply fix → Validate">
              <RemediationPanel incident={incident} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-[3fr_2fr]">
            <Card title="Validation" subtitle="An incident is RESOLVED only when every check passes">
              <ValidationPanel incident={incident} />
            </Card>
            <Card title="Activity">
              <EventLog events={state.events} />
            </Card>
          </div>

          <Card title="Incident report" subtitle="Markdown, saved under artifacts/incidents/">
            <ReportViewer markdown={report} path={incident?.report_path} />
          </Card>
        </div>
      )}
    </main>
  );
}
