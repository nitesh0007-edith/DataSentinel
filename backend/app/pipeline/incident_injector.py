"""Inject realistic code regressions into the monitored pipeline repository.

Each incident is a small source edit committed by a (fictional) developer, just
like a real accidental change. The pipeline still runs to SUCCESS afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import TEMPLATE_REPO_DIR, Settings
from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.models import IncidentType
from app.pipeline.workspace import resolve_in_repo, workspace_git

log = get_logger("injector")


@dataclass(frozen=True)
class IncidentScenario:
    type: IncidentType
    title: str
    description: str
    find: str
    replace: str
    commit_message: str
    author: tuple[str, str]


SCENARIOS: dict[IncidentType, IncidentScenario] = {
    s.type: s
    for s in [
        IncidentScenario(
            type=IncidentType.FILTER_REGRESSION,
            title="Filter regression",
            description="Silver-layer market filter narrowed from UK/Germany/Italy to UK only.",
            find='    df = df[df["country"].isin(["UK", "Germany", "Italy"])]\n',
            replace='    df = df[df["country"] == "UK"]\n',
            commit_message="refactor: simplify market filter in silver layer",
            author=("Jordan Lee", "jordan.lee@datasentinel.example"),
        ),
        IncidentScenario(
            type=IncidentType.NULL_EXPLOSION,
            title="Null explosion",
            description="Gold layer masks sales_rep for Enterprise accounts, nulling a large share of rows.",
            find='    df["revenue"] = df["revenue"].round(2)\n',
            replace=(
                '    df["revenue"] = df["revenue"].round(2)\n'
                '    df["sales_rep"] = df["sales_rep"].where(df["segment"] != "Enterprise")\n'
            ),
            commit_message="feat: hide sales rep for enterprise accounts",
            author=("Priya Shah", "priya.shah@datasentinel.example"),
        ),
        IncidentScenario(
            type=IncidentType.DUPLICATE_INGESTION,
            title="Duplicate ingestion",
            description="Bronze layer re-appends a replay batch, duplicating ~15% of records.",
            find="    df = raw.copy()\n",
            replace="    df = pd.concat([raw, raw.sample(frac=0.15, random_state=7)], ignore_index=True)\n",
            commit_message="fix: include late-arriving records from replay batch",
            author=("Sam Okafor", "sam.okafor@datasentinel.example"),
        ),
        IncidentScenario(
            type=IncidentType.SCHEMA_DRIFT,
            title="Schema drift",
            description="Gold output renames revenue to revenue_amount, breaking downstream consumers.",
            find='    return df[REQUIRED_COLUMNS + ["event_month"]]\n',
            replace='    return df[REQUIRED_COLUMNS + ["event_month"]].rename(columns={"revenue": "revenue_amount"})\n',
            commit_message="chore: align gold column names with finance glossary",
            author=("Alex Moreau", "alex.moreau@datasentinel.example"),
        ),
        IncidentScenario(
            type=IncidentType.REVENUE_SHIFT,
            title="Revenue distribution shift",
            description="Revenue divided by 100 (units bug), shifting the whole distribution.",
            find='    df["revenue"] = df["revenue"].round(2)\n',
            replace='    df["revenue"] = (df["revenue"] / 100).round(2)\n',
            commit_message="chore: normalise revenue to reporting currency units",
            author=("Chris Novak", "chris.novak@datasentinel.example"),
        ),
    ]
}


def list_scenarios() -> list[dict[str, str]]:
    return [
        {"type": s.type.value, "title": s.title, "description": s.description}
        for s in SCENARIOS.values()
    ]


def inject_incident(settings: Settings, incident_type: IncidentType) -> dict[str, str]:
    scenario = SCENARIOS.get(incident_type)
    if scenario is None:
        raise NotFoundError(f"Unknown incident type '{incident_type}'")

    git = workspace_git(settings)
    if not git.is_repo():
        raise ConflictError("Pipeline repository not initialised. Reset the demo first.")
    if not git.is_clean():
        raise ConflictError("Pipeline repository has uncommitted changes; reset the demo first.")

    target = resolve_in_repo(settings.pipeline_repo, settings.transform_module_path)
    source = target.read_text(encoding="utf-8")
    healthy = (TEMPLATE_REPO_DIR / settings.transform_module_path).read_text(encoding="utf-8")
    if source != healthy or source.count(scenario.find) != 1:
        raise ConflictError(
            "Transformation code is not in its healthy state (another incident may already be "
            "injected). Resolve it or reset the demo first."
        )
    target.write_text(source.replace(scenario.find, scenario.replace), encoding="utf-8")
    sha = git.commit_all(scenario.commit_message, *scenario.author)
    log.info("Injected %s as commit %s", incident_type.value, sha[:7])
    return {
        "type": incident_type.value,
        "commit": sha,
        "commit_message": scenario.commit_message,
        "file": settings.transform_module_path,
    }
