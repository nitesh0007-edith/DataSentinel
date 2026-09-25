"""Reset the demo: clean data/artifacts, rebuild the pipeline repo, regenerate data.

Usage: python scripts/reset_demo.py [--rows 110000] [--seed 42] [--baseline]
"""

import argparse

import _bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.workflow import DataSentinelService

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--baseline", action="store_true", help="also run the healthy pipeline and capture the baseline")
    args = parser.parse_args()
    configure_logging()
    svc = DataSentinelService(get_settings())
    state = svc.reset_demo(args.rows, args.seed)
    print(f"Reset complete: {state.dataset.rows:,} rows at {state.dataset.path}")
    if args.baseline:
        run = svc.run_pipeline(set_baseline=True)
        print(f"Baseline {run.run_id}: {run.status.value}, {run.rows_output:,} rows")
