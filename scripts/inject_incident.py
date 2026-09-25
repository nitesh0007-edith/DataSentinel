"""Commit an incident-causing code change into the monitored pipeline repo.

Usage: python scripts/inject_incident.py [filter_regression|null_explosion|duplicate_ingestion|schema_drift|revenue_shift]
"""

import argparse

import _bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.models import IncidentType
from app.services.workflow import DataSentinelService

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    choices = [t.value for t in IncidentType if t is not IncidentType.UNKNOWN]
    parser.add_argument("type", nargs="?", default="filter_regression", choices=choices)
    args = parser.parse_args()
    configure_logging()
    result = DataSentinelService(get_settings()).inject(IncidentType(args.type))
    print(f"Injected {result['type']} as commit {result['commit'][:7]}: {result['commit_message']}")
