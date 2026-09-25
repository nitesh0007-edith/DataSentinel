"""Deterministic synthetic customer revenue data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.core.models import DatasetInfo

log = get_logger("generator")

COUNTRIES = ["UK", "Germany", "Italy"]
COUNTRY_WEIGHTS = [0.40, 0.35, 0.25]
# Mild country-level revenue multipliers keep the data realistic without making
# a country filter change look like a revenue-distribution incident on its own.
COUNTRY_REVENUE_FACTOR = {"UK": 1.00, "Germany": 1.06, "Italy": 0.94}

PRODUCTS = ["Analytics", "CloudStorage", "Security", "Integration", "Support"]
PRODUCT_WEIGHTS = [0.28, 0.24, 0.20, 0.16, 0.12]
PRODUCT_BASE_REVENUE = {
    "Analytics": 1200.0,
    "CloudStorage": 650.0,
    "Security": 1800.0,
    "Integration": 950.0,
    "Support": 400.0,
}

SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
SEGMENT_WEIGHTS = [0.45, 0.30, 0.25]
SEGMENT_FACTOR = {"SMB": 0.6, "Mid-Market": 1.0, "Enterprise": 2.4}

SALES_REPS = [f"rep_{i:02d}" for i in range(24)]
PROVIDERS = [f"PRV-{i:03d}" for i in range(1, 13)]

SALES_REP_NULL_RATE = 0.004
START_DATE = pd.Timestamp("2026-01-01")
DAYS = 180


def generate_customers(rows: int, seed: int) -> pd.DataFrame:
    """Generate a deterministic customer revenue event table."""
    if rows <= 0:
        raise ValueError("rows must be positive")
    rng = np.random.default_rng(seed)

    country = rng.choice(COUNTRIES, size=rows, p=COUNTRY_WEIGHTS)
    product = rng.choice(PRODUCTS, size=rows, p=PRODUCT_WEIGHTS)
    segment = rng.choice(SEGMENTS, size=rows, p=SEGMENT_WEIGHTS)

    base = np.vectorize(PRODUCT_BASE_REVENUE.get)(product)
    seg_factor = np.vectorize(SEGMENT_FACTOR.get)(segment)
    country_factor = np.vectorize(COUNTRY_REVENUE_FACTOR.get)(country)
    noise = rng.lognormal(mean=0.0, sigma=0.35, size=rows)
    revenue = np.round(base * seg_factor * country_factor * noise, 2)

    sales_rep = rng.choice(SALES_REPS, size=rows).astype(object)
    sales_rep[rng.random(rows) < SALES_REP_NULL_RATE] = None

    provider_id = rng.choice(PROVIDERS, size=rows)
    offsets = rng.integers(0, DAYS, size=rows)
    event_date = (START_DATE + pd.to_timedelta(offsets, unit="D")).strftime("%Y-%m-%d")

    customer_num = rng.integers(10_000, 10_000 + max(rows // 2, 1000), size=rows)
    customer_id = np.char.add("CUST-", customer_num.astype(str))

    df = pd.DataFrame(
        {
            "customer_id": customer_id,
            "country": country,
            "product": product,
            "revenue": revenue,
            "segment": segment,
            "sales_rep": sales_rep,
            "provider_id": provider_id,
            "event_date": event_date,
        }
    )
    return df.sort_values(["event_date", "customer_id"], kind="stable").reset_index(drop=True)


def write_dataset(rows: int, seed: int, path: Path) -> DatasetInfo:
    df = generate_customers(rows, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    log.info("Generated %s rows (seed=%s) -> %s", f"{len(df):,}", seed, path)
    return DatasetInfo(path=str(path), rows=len(df), seed=seed, columns=list(df.columns))
