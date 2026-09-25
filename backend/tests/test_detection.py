import pandas as pd

from app.core.config import DetectionThresholds
from app.core.models import DataHealth, Severity
from app.detection.anomaly_engine import detect_anomalies
from app.pipeline.generator import generate_customers
from app.profiling.profiler import profile_dataframe

T = DetectionThresholds()


def _profiles(mutate):
    base_df = generate_customers(4000, seed=3)
    return profile_dataframe(base_df, "base", T), profile_dataframe(mutate(base_df.copy()), "cur", T)


def _rules(report):
    return {a.rule: a for a in report.anomalies}


def test_identical_data_is_healthy():
    base, cur = _profiles(lambda df: df)
    report = detect_anomalies(base, cur, T)
    assert report.data_health == DataHealth.HEALTHY
    assert report.anomalies == []


def test_category_disappearance_and_row_drop():
    base, cur = _profiles(lambda df: df[df["country"] == "UK"])
    report = detect_anomalies(base, cur, T)
    assert report.data_health == DataHealth.CRITICAL
    assert {a.details["value"] for a in report.anomalies if a.rule == "category_disappearance"} == {"Germany", "Italy"}
    assert _rules(report)["row_count"].severity == Severity.CRITICAL
    assert _rules(report)["category_shift"].severity == Severity.CRITICAL


def test_null_rate_drift():
    def mutate(df):
        df.loc[df.index[: len(df) // 3], "sales_rep"] = None
        return df

    report = detect_anomalies(*_profiles(mutate), T)
    assert _rules(report)["null_rate"].column == "sales_rep"
    assert _rules(report)["null_rate"].severity == Severity.CRITICAL


def test_schema_drift():
    report = detect_anomalies(*_profiles(lambda df: df.rename(columns={"revenue": "revenue_amount"})), T)
    schema = [a for a in report.anomalies if a.rule == "schema"]
    assert {a.column for a in schema} == {"revenue", "revenue_amount"}
    assert report.data_health == DataHealth.CRITICAL


def test_duplicate_drift():
    report = detect_anomalies(*_profiles(lambda df: pd.concat([df, df.sample(frac=0.2, random_state=1)])), T)
    assert _rules(report)["duplicates"].severity == Severity.CRITICAL


def test_numeric_drift():
    def mutate(df):
        df["revenue"] = df["revenue"] / 100
        return df

    report = detect_anomalies(*_profiles(mutate), T)
    assert _rules(report)["numeric_drift"].severity == Severity.CRITICAL


def test_thresholds_are_configurable():
    base, cur = _profiles(lambda df: df.iloc[: int(len(df) * 0.85)])
    assert detect_anomalies(base, cur, T).data_health == DataHealth.WARNING
    lenient = DetectionThresholds(row_count_warning=0.5, row_count_critical=0.9)
    assert detect_anomalies(base, cur, lenient).data_health == DataHealth.HEALTHY
