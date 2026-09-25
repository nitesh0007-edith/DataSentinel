"""Regression tests for the customer revenue transformations."""

import pandas as pd

from pipelines.customer_transform import REQUIRED_COLUMNS, to_bronze, to_gold, to_silver

EXPECTED_COUNTRIES = {"UK", "Germany", "Italy"}


def _raw() -> pd.DataFrame:
    rows = []
    for i, country in enumerate(["UK", "Germany", "Italy"] * 4):
        rows.append(
            {
                "customer_id": f"C{i:05d}",
                "country": country,
                "product": "Analytics",
                "revenue": 100.0 + i,
                "segment": ["SMB", "Mid-Market", "Enterprise"][i % 3],
                "sales_rep": f"rep_{i % 5:02d}",
                "provider_id": f"PRV-{i % 3:03d}",
                "event_date": "2026-03-01",
            }
        )
    return pd.DataFrame(rows)


def _run(raw: pd.DataFrame) -> pd.DataFrame:
    return to_gold(to_silver(to_bronze(raw)))


def test_all_markets_retained():
    gold = _run(_raw())
    assert set(gold["country"]) == EXPECTED_COUNTRIES


def test_no_rows_lost_for_clean_input():
    raw = _raw()
    assert len(_run(raw)) == len(raw)


def test_gold_schema():
    gold = _run(_raw())
    assert list(gold.columns) == REQUIRED_COLUMNS + ["event_month"]


def test_no_duplicates_introduced():
    gold = _run(_raw())
    assert not gold.duplicated().any()


def test_revenue_preserved():
    raw = _raw()
    gold = _run(raw)
    assert abs(gold["revenue"].sum() - raw["revenue"].sum()) < 0.01


def test_sales_rep_populated():
    gold = _run(_raw())
    assert gold["sales_rep"].notna().all()
