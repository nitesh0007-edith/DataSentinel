"""
Customer revenue pipeline: Bronze -> Silver -> Gold transformations.

Owner:     Data Platform team
Consumers: EMEA revenue dashboards, finance month-end reporting

The runner calls to_bronze, to_silver and to_gold in order.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "customer_id",
    "country",
    "product",
    "revenue",
    "segment",
    "sales_rep",
    "provider_id",
    "event_date",
]

STRING_COLUMNS = ["country", "product", "segment", "sales_rep", "provider_id"]


def to_bronze(raw: pd.DataFrame) -> pd.DataFrame:
    """Standardise raw landing data: enforce types and trim strings."""
    df = raw.copy()
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Raw data missing required columns: {missing}")
    df["event_date"] = pd.to_datetime(df["event_date"])
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    for col in STRING_COLUMNS:
        df[col] = df[col].astype("string").str.strip()
    return df


def to_silver(bronze: pd.DataFrame) -> pd.DataFrame:
    """Apply business filters and cleansing rules."""
    df = bronze.dropna(subset=["customer_id", "revenue"])
    df = df[df["revenue"] >= 0]
    # Retain every in-scope EMEA market (UK, Germany, Italy).
    df = df[df["country"].isin(["UK", "Germany", "Italy"])]
    return df.reset_index(drop=True)


def to_gold(silver: pd.DataFrame) -> pd.DataFrame:
    """Produce the reporting-ready customer revenue table."""
    df = silver.copy()
    df["event_month"] = df["event_date"].dt.to_period("M").astype(str)
    df["revenue"] = df["revenue"].round(2)
    return df[REQUIRED_COLUMNS + ["event_month"]]
