"""Deterministic, explainable anomaly rules. No LLM involvement."""

from __future__ import annotations

from app.core.config import DetectionThresholds
from app.core.models import Anomaly, DatasetProfile, Severity


def _grade(value: float, warning: float, critical: float, info: float | None = None) -> Severity | None:
    if value >= critical:
        return Severity.CRITICAL
    if value >= warning:
        return Severity.WARNING
    if info is not None and value >= info:
        return Severity.INFO
    return None


def row_count_rule(base: DatasetProfile, cur: DatasetProfile, t: DetectionThresholds) -> list[Anomaly]:
    if base.row_count == 0:
        return []
    change = (cur.row_count - base.row_count) / base.row_count
    sev = _grade(abs(change), t.row_count_warning, t.row_count_critical, t.row_count_info)
    if sev is None:
        return []
    direction = "decreased" if change < 0 else "increased"
    return [
        Anomaly(
            id="row_count",
            rule="row_count",
            severity=sev,
            title=f"Row count {direction} {abs(change):.1%}",
            description=(
                f"Gold output has {cur.row_count:,} rows vs {base.row_count:,} in the healthy "
                f"baseline ({cur.row_count - base.row_count:+,} rows)."
            ),
            baseline_value=base.row_count,
            current_value=cur.row_count,
            delta=round(change, 6),
        )
    ]


def schema_rule(base: DatasetProfile, cur: DatasetProfile, t: DetectionThresholds) -> list[Anomaly]:
    diff = schema_diff(base, cur)
    out: list[Anomaly] = []
    for col in diff["missing_columns"]:
        out.append(Anomaly(
            id=f"schema_missing:{col}", rule="schema", severity=Severity.CRITICAL, column=col,
            title=f"Column '{col}' missing",
            description=f"Column '{col}' ({base.columns[col].dtype}) exists in the baseline but not in the current output.",
            baseline_value=base.columns[col].dtype, current_value=None,
        ))
    for col in diff["new_columns"]:
        out.append(Anomaly(
            id=f"schema_new:{col}", rule="schema", severity=Severity.WARNING, column=col,
            title=f"Unexpected column '{col}'",
            description=f"Column '{col}' ({cur.columns[col].dtype}) appeared that is not in the baseline schema.",
            baseline_value=None, current_value=cur.columns[col].dtype,
        ))
    for col, change in diff["type_changes"].items():
        out.append(Anomaly(
            id=f"schema_type:{col}", rule="schema", severity=Severity.WARNING, column=col,
            title=f"Column '{col}' type changed",
            description=f"Column '{col}' changed type from {change['baseline']} to {change['current']}.",
            baseline_value=change["baseline"], current_value=change["current"],
        ))
    return out


def null_rate_rule(base: DatasetProfile, cur: DatasetProfile, t: DetectionThresholds) -> list[Anomaly]:
    out: list[Anomaly] = []
    for name, bcol in base.columns.items():
        ccol = cur.columns.get(name)
        if ccol is None:
            continue
        delta = ccol.null_pct - bcol.null_pct
        sev = _grade(delta, t.null_rate_warning, t.null_rate_critical)
        if sev is None:
            continue
        out.append(Anomaly(
            id=f"null_rate:{name}", rule="null_rate", severity=sev, column=name,
            title=f"Null rate spike in '{name}'",
            description=(
                f"'{name}' null rate rose from {bcol.null_pct:.2%} to {ccol.null_pct:.2%} "
                f"({ccol.null_count:,} null rows)."
            ),
            baseline_value=bcol.null_pct, current_value=ccol.null_pct, delta=round(delta, 6),
        ))
    return out


def duplicate_rule(base: DatasetProfile, cur: DatasetProfile, t: DetectionThresholds) -> list[Anomaly]:
    delta = cur.duplicate_pct - base.duplicate_pct
    sev = _grade(delta, t.duplicate_warning, t.duplicate_critical)
    if sev is None:
        return []
    return [Anomaly(
        id="duplicates", rule="duplicates", severity=sev,
        title=f"Duplicate rows rose to {cur.duplicate_pct:.2%}",
        description=(
            f"{cur.duplicate_count:,} fully duplicated rows in the current output vs "
            f"{base.duplicate_count:,} in the baseline."
        ),
        baseline_value=base.duplicate_pct, current_value=cur.duplicate_pct, delta=round(delta, 6),
    )]


def categorical_rules(base: DatasetProfile, cur: DatasetProfile, t: DetectionThresholds) -> list[Anomaly]:
    out: list[Anomaly] = []
    for name, bcol in base.columns.items():
        ccol = cur.columns.get(name)
        if not bcol.is_categorical or not bcol.frequencies or ccol is None:
            continue
        cur_freq = ccol.frequencies or {}

        vanished = sorted(
            (v for v, share in bcol.frequencies.items()
             if share >= t.category_min_baseline_share and cur_freq.get(v, 0.0) == 0.0),
            key=lambda v: -bcol.frequencies[v],
        )
        for value in vanished:
            out.append(Anomaly(
                id=f"category_disappearance:{name}:{value}", rule="category_disappearance",
                severity=Severity.CRITICAL, column=name,
                title=f"{name} = '{value}' disappeared",
                description=(
                    f"'{value}' made up {bcol.frequencies[value]:.1%} of '{name}' in the baseline "
                    f"and has 0 rows in the current output."
                ),
                baseline_value=bcol.frequencies[value], current_value=0.0,
                details={"value": value},
            ))

        keys = set(bcol.frequencies) | set(cur_freq)
        tvd = 0.5 * sum(abs(bcol.frequencies.get(k, 0.0) - cur_freq.get(k, 0.0)) for k in keys)
        sev = _grade(tvd, t.category_shift_warning, t.category_shift_critical)
        if sev is not None:
            new_values = sorted(k for k in cur_freq if k not in bcol.frequencies)
            out.append(Anomaly(
                id=f"category_shift:{name}", rule="category_shift", severity=sev, column=name,
                title=f"'{name}' distribution shifted",
                description=(
                    f"Total variation distance between baseline and current '{name}' "
                    f"distributions is {tvd:.2f}."
                    + (f" New values: {', '.join(new_values)}." if new_values else "")
                ),
                baseline_value=bcol.frequencies, current_value=cur_freq, delta=round(tvd, 6),
                details={"tvd": round(tvd, 6), "new_values": new_values},
            ))
    return out


def numeric_rules(base: DatasetProfile, cur: DatasetProfile, t: DetectionThresholds) -> list[Anomaly]:
    out: list[Anomaly] = []
    for name, bcol in base.columns.items():
        ccol = cur.columns.get(name)
        if bcol.numeric is None or ccol is None or ccol.numeric is None:
            continue
        b, c = bcol.numeric, ccol.numeric
        if b.mean == 0:
            continue
        mean_change = (c.mean - b.mean) / abs(b.mean)
        median_change = (c.median - b.median) / abs(b.median) if b.median else 0.0
        magnitude = max(abs(mean_change), abs(median_change))
        sev = _grade(magnitude, t.numeric_mean_warning, t.numeric_mean_critical)
        if sev is None:
            continue
        out.append(Anomaly(
            id=f"numeric_drift:{name}", rule="numeric_drift", severity=sev, column=name,
            title=f"'{name}' distribution drift ({mean_change:+.1%} mean)",
            description=(
                f"'{name}' mean moved from {b.mean:,.2f} to {c.mean:,.2f} ({mean_change:+.1%}); "
                f"median {b.median:,.2f} -> {c.median:,.2f} ({median_change:+.1%})."
            ),
            baseline_value={"mean": b.mean, "median": b.median, "std": b.std},
            current_value={"mean": c.mean, "median": c.median, "std": c.std},
            delta=round(mean_change, 6),
        ))
    return out


def schema_diff(base: DatasetProfile, cur: DatasetProfile) -> dict:
    b, c = base.schema_map, cur.schema_map
    return {
        "missing_columns": [k for k in b if k not in c],
        "new_columns": [k for k in c if k not in b],
        "type_changes": {k: {"baseline": b[k], "current": c[k]} for k in b if k in c and b[k] != c[k]},
    }


ALL_RULES = (row_count_rule, schema_rule, null_rate_rule, duplicate_rule, categorical_rules, numeric_rules)
