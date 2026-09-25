"""Run the pipeline once (optionally capturing the healthy baseline) and optionally detect.

Usage: python scripts/run_pipeline.py [--baseline] [--detect]
"""

import argparse

import _bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.workflow import DataSentinelService

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--detect", action="store_true")
    args = parser.parse_args()
    configure_logging()
    svc = DataSentinelService(get_settings())
    run = svc.run_pipeline(set_baseline=args.baseline)
    print(f"{run.run_id}: Pipeline Status = {run.status.value} ({run.rows_input:,} -> {run.rows_output:,} rows)")
    if args.detect and not args.baseline:
        result = svc.detect()
        det = result["detection"]
        print(f"Data Health = {det.data_health.value}")
        for a in det.anomalies:
            print(f"  [{a.severity.value}] {a.title}")
        if result["incident"]:
            print(f"Incident opened: {result['incident'].id}")
