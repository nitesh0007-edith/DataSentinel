"use client";

import type { DashboardState } from "@/types";
import { Spinner } from "./ui";

export type ActionKey =
  | "reset"
  | "healthy"
  | "inject"
  | "run"
  | "detect"
  | "investigate"
  | "fix"
  | "reject"
  | "apply"
  | "validate"
  | "rollback";

export const ACTION_LABELS: Record<ActionKey, string> = {
  reset: "Reset Demo",
  healthy: "Run Healthy Pipeline",
  inject: "Inject Incident",
  run: "Run Pipeline",
  detect: "Detect",
  investigate: "Investigate",
  fix: "Generate Fix",
  reject: "Reject Fix",
  apply: "Apply Fix",
  validate: "Validate",
  rollback: "Roll Back Fix",
};

export function availability(s: DashboardState | null): Record<ActionKey, boolean> {
  const inc = s?.active_incident ?? null;
  const open = !!inc && inc.status !== "RESOLVED";
  const repo = !!s?.repository.initialised && !!s?.dataset;
  const hasBaseline = !!s?.baseline_run_id;
  const latest = s?.latest_run ?? null;
  return {
    reset: true,
    healthy: repo && !s?.injected_incident,
    inject: repo && hasBaseline && !s?.injected_incident,
    run: repo && hasBaseline,
    detect: hasBaseline && !!latest && latest.status === "SUCCESS" && !latest.is_baseline,
    investigate: open && ["DETECTED", "ROOT_CAUSE_IDENTIFIED", "FIX_REJECTED"].includes(inc!.status),
    fix: open && !!inc!.rca && ["ROOT_CAUSE_IDENTIFIED", "FIX_REJECTED"].includes(inc!.status),
    reject: open && inc!.patch?.status === "PROPOSED",
    apply: open && inc!.patch?.status === "PROPOSED",
    validate: open && ["FIX_APPLIED", "VALIDATION_FAILED"].includes(inc!.status),
    rollback: open && inc!.status === "VALIDATION_FAILED" && inc!.patch?.status === "APPLIED",
  };
}

export function nextAction(s: DashboardState | null): ActionKey | null {
  if (!s || !s.repository.initialised || !s.dataset) return "reset";
  if (!s.baseline_run_id) return "healthy";
  const inc = s.active_incident;
  const latest = s.latest_run;
  if (inc && inc.status !== "RESOLVED") {
    switch (inc.status) {
      case "DETECTED":
        return "investigate";
      case "ROOT_CAUSE_IDENTIFIED":
      case "FIX_REJECTED":
        return "fix";
      case "FIX_PROPOSED":
        return "apply";
      case "VALIDATION_FAILED":
        return "rollback";
      default:
        return "validate";
    }
  }
  if (!s.injected_incident) return "inject";
  if (latest && latest.git_commit !== s.repository.head) return "run";
  if (latest && latest.data_health === "UNKNOWN") return "detect";
  return "run";
}

const FLOW: ActionKey[][] = [
  ["reset", "healthy"],
  ["inject", "run", "detect"],
  ["investigate", "fix", "reject", "apply", "validate", "rollback"],
];

export function ControlBar({
  state,
  busy,
  onAction,
  incidentType,
  setIncidentType,
}: {
  state: DashboardState | null;
  busy: ActionKey | null;
  onAction: (a: ActionKey) => void;
  incidentType: string;
  setIncidentType: (t: string) => void;
}) {
  const avail = availability(state);
  const next = nextAction(state);
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
      {FLOW.map((group, gi) => (
        <div key={gi} className="flex flex-wrap items-center gap-2">
          {gi > 0 && <span className="mr-1 hidden h-6 w-px bg-line md:block" />}
          {group.map((key) => {
            const isNext = key === next && !busy;
            const disabled = !!busy || !avail[key];
            const danger = key === "inject" || key === "reject" || key === "rollback";
            return (
              <span key={key} className="flex items-center gap-2">
                {key === "inject" && (
                  <select
                    aria-label="Incident type"
                    value={incidentType}
                    onChange={(e) => setIncidentType(e.target.value)}
                    disabled={!!busy}
                    className="h-9 rounded-lg border border-line bg-surface px-2 text-sm text-ink"
                  >
                    {(state?.incident_types ?? [{ type: "filter_regression", title: "Filter regression" }]).map((t) => (
                      <option key={t.type} value={t.type}>{t.title}</option>
                    ))}
                  </select>
                )}
                <button
                  onClick={() => onAction(key)}
                  disabled={disabled}
                  className={[
                    "inline-flex h-9 items-center gap-2 rounded-lg px-3.5 text-sm font-medium transition",
                    "disabled:cursor-not-allowed disabled:opacity-40",
                    isNext && !disabled
                      ? "bg-accent text-white shadow-sm ring-2 ring-accent/30 hover:brightness-110"
                      : danger
                        ? "border border-critical/40 bg-surface text-critical-ink hover:bg-critical-soft"
                        : "border border-line bg-surface text-ink hover:bg-surface-2",
                  ].join(" ")}
                >
                  {busy === key && <Spinner />}
                  {ACTION_LABELS[key]}
                </button>
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
}
