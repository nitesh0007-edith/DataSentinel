// Mirrors backend/app/core/models.py

export type Severity = "INFO" | "WARNING" | "CRITICAL";
export type DataHealth = "UNKNOWN" | "HEALTHY" | "WARNING" | "CRITICAL";
export type RunStatus = "SUCCESS" | "FAILED";
export type IncidentStatus =
  | "DETECTED"
  | "INVESTIGATING"
  | "ROOT_CAUSE_IDENTIFIED"
  | "FIX_PROPOSED"
  | "FIX_APPLIED"
  | "FIX_REJECTED"
  | "RESOLVED"
  | "VALIDATION_FAILED";

export interface StageMetrics {
  stage: string;
  rows_in: number;
  rows_out: number;
  duration_ms: number;
}

export interface PipelineRun {
  run_id: string;
  timestamp: string;
  status: RunStatus;
  rows_input: number;
  rows_output: number;
  duration_ms: number;
  stages: StageMetrics[];
  schema_snapshot: Record<string, string>;
  quality_metrics: Record<string, number>;
  logs: string[];
  git_commit: string | null;
  git_commit_message: string | null;
  error: string | null;
  is_baseline: boolean;
  purpose: string;
  data_health: DataHealth;
  incident_id: string | null;
}

export interface NumericStats {
  min: number;
  max: number;
  mean: number;
  median: number;
  std: number;
  quantiles: Record<string, number>;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  null_count: number;
  null_pct: number;
  unique_count: number;
  numeric: NumericStats | null;
  frequencies: Record<string, number> | null;
  is_categorical: boolean;
}

export interface DatasetProfile {
  run_id: string;
  row_count: number;
  column_count: number;
  duplicate_count: number;
  duplicate_pct: number;
  columns: Record<string, ColumnProfile>;
}

export interface Anomaly {
  id: string;
  rule: string;
  severity: Severity;
  title: string;
  description: string;
  column: string | null;
  delta: number | null;
  details: Record<string, unknown>;
}

export interface DetectionReport {
  run_id: string;
  baseline_run_id: string;
  data_health: DataHealth;
  severity: Severity | null;
  anomalies: Anomaly[];
  row_count_baseline: number;
  row_count_current: number;
  row_count_change_pct: number;
  summary: string;
}

export interface CommitInfo {
  sha: string;
  short_sha: string;
  author: string;
  date: string;
  message: string;
}

export interface CommitEvidence {
  commit: CommitInfo;
  changed_files: string[];
  diff: string;
}

export interface SuspectChange {
  commit_sha: string;
  file: string;
  line: number | null;
  removed: string[];
  added: string[];
  score: number;
  signals: string[];
}

export interface SourceSnippet {
  file: string;
  start_line: number;
  end_line: number;
  content: string;
}

export interface EvidencePackage {
  baseline_commit: string | null;
  head_commit: string | null;
  changed_files: string[];
  commits_since_baseline: CommitEvidence[];
  recent_commits: CommitInfo[];
  source_snippets: SourceSnippet[];
  suspect_changes: SuspectChange[];
  schema_differences: Record<string, unknown>;
  category_disappearance: Record<string, string[]>;
}

export interface RootCauseAnalysis {
  incident_type: string;
  severity: Severity;
  likely_root_cause: string;
  file: string | null;
  line: number | null;
  commit: string | null;
  commit_message: string | null;
  confidence: number;
  impact: string;
  recommended_fix: string;
  observed_facts: string[];
  inferences: string[];
  insufficient_evidence: boolean;
  engine: string;
  engine_notes: string[];
}

export interface PatchProposal {
  patch_id: string;
  file: string;
  commit_reverted: string | null;
  description: string;
  diff: string;
  status: "PROPOSED" | "APPLIED" | "REJECTED" | "ROLLED_BACK";
  applied_commit: string | null;
  rolled_back_at: string | null;
  rollback_commit: string | null;
}

export interface ValidationCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface ValidationResult {
  run_id: string | null;
  passed: boolean;
  checks: ValidationCheck[];
}

export interface InvestigationStep {
  key: string;
  label: string;
  status: "done" | "failed" | "skipped";
  detail: string;
  duration_ms: number;
}

export interface Incident {
  id: string;
  created_at: string;
  status: IncidentStatus;
  severity: Severity;
  run_id: string;
  baseline_run_id: string;
  detection: DetectionReport;
  investigation_steps: InvestigationStep[];
  evidence: EvidencePackage | null;
  rca: RootCauseAnalysis | null;
  patch: PatchProposal | null;
  validation: ValidationResult | null;
  report_path: string | null;
  resolved_at: string | null;
}

export interface TimelineEvent {
  timestamp: string;
  kind: string;
  message: string;
  severity: Severity | null;
}

export interface IncidentTypeInfo {
  type: string;
  title: string;
  description: string;
}

export interface DashboardState {
  dataset: { rows: number; seed: number; path: string } | null;
  runs: PipelineRun[];
  latest_run: PipelineRun | null;
  baseline_run_id: string | null;
  baseline_profile: DatasetProfile | null;
  latest_profile: DatasetProfile | null;
  last_detection: DetectionReport | null;
  active_incident: Incident | null;
  incidents: Incident[];
  injected_incident: string | null;
  events: TimelineEvent[];
  repository: {
    path: string;
    initialised: boolean;
    head?: string;
    clean?: boolean;
    recent_commits?: CommitInfo[];
  };
  rca_engine: string;
  incident_types: IncidentTypeInfo[];
}
