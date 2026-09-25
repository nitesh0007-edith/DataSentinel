"""Run the complete P0 demo end to end without the UI and print each step.

Usage: python scripts/run_golden_path.py [--type filter_regression] [--rows 110000]
Exits non-zero if the incident does not end RESOLVED.
"""

import argparse
import sys

import _bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.models import IncidentStatus, IncidentType
from app.services.workflow import DataSentinelService

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", default="filter_regression")
    parser.add_argument("--rows", type=int, default=None)
    args = parser.parse_args()
    configure_logging()
    svc = DataSentinelService(get_settings())

    svc.reset_demo(args.rows)
    base = svc.run_pipeline(set_baseline=True)
    print(f"1. Healthy baseline {base.run_id}: {base.status.value}, {base.rows_output:,} rows")
    inj = svc.inject(IncidentType(args.type))
    print(f"2. Injected {inj['type']} ({inj['commit'][:7]} {inj['commit_message']})")
    run = svc.run_pipeline()
    print(f"3. Pipeline Status = {run.status.value}, {run.rows_output:,} rows")
    result = svc.detect()
    inc = result["incident"]
    print(f"4. Data Health = {result['detection'].data_health.value}; incident {inc.id if inc else None}")
    if inc is None:
        sys.exit("No incident detected")
    inc = svc.investigate(inc.id)
    print(f"5. Root cause ({inc.rca.engine}, {inc.rca.confidence:.0%}): {inc.rca.file}:{inc.rca.line}\n   {inc.rca.likely_root_cause}")
    inc = svc.propose_fix(inc.id)
    print(f"6. Proposed patch:\n{inc.patch.diff}")
    inc = svc.apply_fix(inc.id)
    print(f"7. Applied as commit {inc.patch.applied_commit[:7]}")
    inc = svc.validate(inc.id)
    for c in inc.validation.checks:
        print(f"   {'✓' if c.passed else '✗'} {c.name}: {c.detail}")
    print(f"8. Incident {inc.id}: {inc.status.value}. Report: {inc.report_path}")
    sys.exit(0 if inc.status == IncidentStatus.RESOLVED else 1)
