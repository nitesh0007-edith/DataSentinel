"""Domain models shared across DataSentinel modules."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return {"INFO": 1, "WARNING": 2, "CRITICAL": 3}[self.value]


class DataHealth(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class RunStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class IncidentType(str, Enum):
    FILTER_REGRESSION = "filter_regression"
    NULL_EXPLOSION = "null_explosion"
    DUPLICATE_INGESTION = "duplicate_ingestion"
    SCHEMA_DRIFT = "schema_drift"
    REVENUE_SHIFT = "revenue_shift"
    UNKNOWN = "unknown"


class IncidentStatus(str, Enum):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    FIX_PROPOSED = "FIX_PROPOSED"
    FIX_APPLIED = "FIX_APPLIED"
    FIX_REJECTED = "FIX_REJECTED"
    RESOLVED = "RESOLVED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


# ---------------------------------------------------------------- data / runs


class DatasetInfo(BaseModel):
    path: str
    rows: int
    seed: int
    columns: list[str]
    generated_at: datetime = Field(default_factory=utcnow)


class StageMetrics(BaseModel):
    stage: str
    rows_in: int
    rows_out: int
    duration_ms: float


class PipelineRun(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    status: RunStatus
    rows_input: int
    rows_output: int
    duration_ms: float
    stages: list[StageMetrics] = []
    schema_snapshot: dict[str, str] = {}
    quality_metrics: dict[str, float] = {}
    logs: list[str] = []
    git_commit: str | None = None
    git_commit_message: str | None = None
    profile_path: str | None = None
    output_path: str | None = None
    error: str | None = None
    is_baseline: bool = False
    purpose: str = "manual"  # manual | baseline | validation
    data_health: DataHealth = DataHealth.UNKNOWN  # set once DataSentinel checks the run
    incident_id: str | None = None


# ---------------------------------------------------------------- profiling


class NumericStats(BaseModel):
    min: float
    max: float
    mean: float
    median: float
    std: float
    quantiles: dict[str, float]


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    numeric: NumericStats | None = None
    # category -> share of non-null rows (only for categorical columns)
    frequencies: dict[str, float] | None = None
    top_values: list[tuple[str, int]] | None = None
    is_categorical: bool = False


class DatasetProfile(BaseModel):
    run_id: str
    created_at: datetime = Field(default_factory=utcnow)
    row_count: int
    column_count: int
    duplicate_count: int
    duplicate_pct: float
    columns: dict[str, ColumnProfile]

    @property
    def schema_map(self) -> dict[str, str]:
        return {name: col.dtype for name, col in self.columns.items()}


# ---------------------------------------------------------------- detection


class Anomaly(BaseModel):
    id: str
    rule: str  # row_count | null_rate | schema | duplicates | category_disappearance | category_shift | numeric_drift
    severity: Severity
    title: str
    description: str
    column: str | None = None
    baseline_value: Any = None
    current_value: Any = None
    delta: float | None = None
    details: dict[str, Any] = {}


class DetectionReport(BaseModel):
    run_id: str
    baseline_run_id: str
    created_at: datetime = Field(default_factory=utcnow)
    data_health: DataHealth
    severity: Severity | None
    anomalies: list[Anomaly]
    row_count_baseline: int
    row_count_current: int
    row_count_change_pct: float
    summary: str


# ---------------------------------------------------------------- git / evidence


class CommitInfo(BaseModel):
    sha: str
    short_sha: str
    author: str
    date: str
    message: str


class DiffLine(BaseModel):
    kind: str  # "+", "-", " "
    content: str
    old_lineno: int | None = None
    new_lineno: int | None = None


class DiffHunk(BaseModel):
    file: str
    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]

    @property
    def added(self) -> list[DiffLine]:
        return [line for line in self.lines if line.kind == "+"]

    @property
    def removed(self) -> list[DiffLine]:
        return [line for line in self.lines if line.kind == "-"]


class CommitEvidence(BaseModel):
    commit: CommitInfo
    changed_files: list[str]
    diff: str
    hunks: list[DiffHunk]


class SourceSnippet(BaseModel):
    file: str
    start_line: int
    end_line: int
    content: str  # line-numbered text


class SuspectChange(BaseModel):
    """A diff hunk scored for relevance to the observed anomalies (deterministic)."""

    commit_sha: str
    file: str
    line: int | None
    removed: list[str]
    added: list[str]
    score: float
    signals: list[str]


class EvidencePackage(BaseModel):
    incident_id: str
    created_at: datetime = Field(default_factory=utcnow)
    anomaly_summary: str
    anomalies: list[Anomaly]
    baseline_profile: DatasetProfile
    current_profile: DatasetProfile
    schema_differences: dict[str, Any]
    category_disappearance: dict[str, list[str]]
    pipeline_run: PipelineRun
    baseline_run: PipelineRun
    logs: list[str]
    baseline_commit: str | None
    head_commit: str | None
    recent_commits: list[CommitInfo]
    commits_since_baseline: list[CommitEvidence]
    changed_files: list[str]
    source_snippets: list[SourceSnippet]
    suspect_changes: list[SuspectChange]


# ---------------------------------------------------------------- RCA / remediation / validation


class RootCauseAnalysis(BaseModel):
    incident_type: IncidentType
    severity: Severity
    likely_root_cause: str
    file: str | None
    line: int | None
    commit: str | None
    commit_message: str | None = None
    confidence: float
    impact: str
    recommended_fix: str
    observed_facts: list[str] = []
    inferences: list[str] = []
    insufficient_evidence: bool = False
    engine: str  # "heuristic" or "llm:<provider>/<model>"
    engine_notes: list[str] = []


class PatchProposal(BaseModel):
    patch_id: str
    incident_id: str
    file: str
    commit_reverted: str | None
    description: str
    diff: str
    base_sha256: str
    proposed_sha256: str
    status: str = "PROPOSED"  # PROPOSED | APPLIED | REJECTED | ROLLED_BACK
    created_at: datetime = Field(default_factory=utcnow)
    applied_at: datetime | None = None
    applied_commit: str | None = None
    diff_path: str | None = None
    rolled_back_at: datetime | None = None
    rollback_commit: str | None = None


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ValidationResult(BaseModel):
    run_id: str | None
    passed: bool
    checks: list[ValidationCheck]
    detection: DetectionReport | None = None
    created_at: datetime = Field(default_factory=utcnow)


class InvestigationStep(BaseModel):
    key: str
    label: str
    status: str  # done | failed | skipped
    detail: str
    duration_ms: float


class Incident(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    status: IncidentStatus
    severity: Severity
    run_id: str
    baseline_run_id: str
    detection: DetectionReport
    investigation_steps: list[InvestigationStep] = []
    evidence: EvidencePackage | None = None
    rca: RootCauseAnalysis | None = None
    patch: PatchProposal | None = None
    validation: ValidationResult | None = None
    report_path: str | None = None
    resolved_at: datetime | None = None


class TimelineEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utcnow)
    kind: str
    message: str
    severity: Severity | None = None


class DemoState(BaseModel):
    dataset: DatasetInfo | None = None
    runs: list[PipelineRun] = []
    baseline_run_id: str | None = None
    last_detection: DetectionReport | None = None
    incidents: dict[str, Incident] = {}
    active_incident_id: str | None = None
    injected_incident: str | None = None
    events: list[TimelineEvent] = []
    run_counter: int = 0
    incident_counter: int = 0
