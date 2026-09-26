"""Shared API dependencies.

IMPORTANT — single-process constraint
--------------------------------------
``get_service()`` returns a process-scoped singleton backed by a
``threading.RLock`` and a JSON file on disk.  This architecture is correct
for a **single-worker** deployment (the default ``uvicorn app.main:app
--reload`` dev server).

Running with multiple worker processes (e.g. ``--workers N`` or gunicorn
with N>1 workers) will produce silent state divergence: each worker has its
own ``lru_cache`` instance and its own lock, so concurrent mutations from
different workers will silently overwrite each other in the JSON state file.

Do NOT deploy with WEB_CONCURRENCY > 1 or multiple gunicorn/uvicorn workers.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.workflow import DataSentinelService


@lru_cache
def get_service() -> DataSentinelService:
    return DataSentinelService(get_settings())
