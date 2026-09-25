import pandas as pd

from app.profiling.profiler import profile_dataframe


def test_profile_metrics():
    df = pd.DataFrame(
        {
            "country": ["UK", "UK", "Germany", None],
            "revenue": [10.0, 20.0, 30.0, 40.0],
        }
    )
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # one duplicate row
    p = profile_dataframe(df, "run-x")
    assert p.row_count == 5
    assert p.column_count == 2
    assert p.duplicate_count == 1
    assert p.duplicate_pct == 0.2

    country = p.columns["country"]
    assert country.null_count == 1
    assert country.is_categorical
    assert country.frequencies == {"UK": 0.75, "Germany": 0.25}

    rev = p.columns["revenue"].numeric
    assert rev is not None
    assert rev.min == 10.0 and rev.max == 40.0
    assert rev.median == 20.0
    assert "p95" in rev.quantiles
