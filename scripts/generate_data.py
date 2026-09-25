"""Generate the deterministic synthetic customer dataset.

Usage: python scripts/generate_data.py [--rows 110000] [--seed 42]
"""

import argparse

import _bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.pipeline.generator import write_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    settings = get_settings()
    parser.add_argument("--rows", type=int, default=settings.default_rows)
    parser.add_argument("--seed", type=int, default=settings.default_seed)
    args = parser.parse_args()
    configure_logging()
    info = write_dataset(args.rows, args.seed, settings.raw_data_path)
    print(f"Wrote {info.rows:,} rows to {info.path}")
