import pandas as pd

from app.pipeline.generator import COUNTRIES, generate_customers

REQUIRED = ["customer_id", "country", "product", "revenue", "segment", "sales_rep", "provider_id", "event_date"]


def test_required_columns_and_size():
    df = generate_customers(5000, seed=1)
    assert list(df.columns) == REQUIRED
    assert len(df) == 5000


def test_deterministic_for_same_seed():
    pd.testing.assert_frame_equal(generate_customers(3000, 7), generate_customers(3000, 7))


def test_different_seed_differs():
    assert not generate_customers(3000, 7).equals(generate_customers(3000, 8))


def test_all_countries_present_and_revenue_positive():
    df = generate_customers(5000, seed=42)
    assert set(df["country"]) == set(COUNTRIES)
    assert (df["revenue"] > 0).all()
    assert not df.duplicated().any()
