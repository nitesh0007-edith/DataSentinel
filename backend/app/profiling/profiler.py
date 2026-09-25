"""Dataset profiling: deterministic statistics, stored as JSON."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.config import DetectionThresholds
from app.core.models import ColumnProfile, DatasetProfile, NumericStats
from app.core.state import write_text_atomic

QUANTILES = (0.01, 0.05, 0.25, 0.75, 0.95, 0.99)
TOP_N = 10


def _is_categorical(series: pd.Series, unique: int, max_unique: int) -> bool:
    if pd.api.types.is_bool_dtype(series):
        return True
    is_text = pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)
    return bool(is_text and unique <= max_unique)


def profile_dataframe(
    df: pd.DataFrame, run_id: str, thresholds: DetectionThresholds | None = None
) -> DatasetProfile:
    thresholds = thresholds or DetectionThresholds()
    rows = len(df)
    duplicate_count = int(df.duplicated().sum()) if rows else 0

    columns: dict[str, ColumnProfile] = {}
    for name in df.columns:
        s = df[name]
        null_count = int(s.isna().sum())
        unique = int(s.nunique(dropna=True))
        col = ColumnProfile(
            name=str(name),
            dtype=str(s.dtype),
            null_count=null_count,
            null_pct=round(null_count / rows, 6) if rows else 0.0,
            unique_count=unique,
        )
        non_null = s.dropna()

        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and len(non_null):
            q = non_null.quantile(list(QUANTILES))
            col.numeric = NumericStats(
                min=float(non_null.min()),
                max=float(non_null.max()),
                mean=float(non_null.mean()),
                median=float(non_null.median()),
                std=float(non_null.std(ddof=0)),
                quantiles={f"p{int(k * 100)}": float(v) for k, v in q.items()},
            )
        elif len(non_null) and not pd.api.types.is_datetime64_any_dtype(s):
            counts = non_null.astype(str).value_counts()
            col.top_values = [(str(k), int(v)) for k, v in counts.head(TOP_N).items()]
            if _is_categorical(s, unique, thresholds.categorical_max_unique):
                col.is_categorical = True
                total = counts.sum()
                col.frequencies = {str(k): round(float(v) / float(total), 6) for k, v in counts.items()}
        columns[str(name)] = col

    return DatasetProfile(
        run_id=run_id,
        row_count=rows,
        column_count=len(df.columns),
        duplicate_count=duplicate_count,
        duplicate_pct=round(duplicate_count / rows, 6) if rows else 0.0,
        columns=columns,
    )


def save_profile(profile: DatasetProfile, path: Path) -> Path:
    write_text_atomic(path, profile.model_dump_json(indent=2))
    return path


def load_profile(path: Path) -> DatasetProfile:
    return DatasetProfile.model_validate_json(path.read_text(encoding="utf-8"))
