"""Shared API dependencies."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.workflow import DataSentinelService


@lru_cache
def get_service() -> DataSentinelService:
    return DataSentinelService(get_settings())
