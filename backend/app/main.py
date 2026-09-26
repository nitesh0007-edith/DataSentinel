"""FastAPI application entrypoint: ``uvicorn app.main:app --reload`` from backend/."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health_router, router
from app.core.config import get_settings
from app.core.errors import DataSentinelError
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("api")


def _warn_if_multi_worker() -> None:
    """Emit a prominent warning when the process detects a multi-worker configuration.

    DataSentinel uses a single JSON file + threading.RLock for state, which is
    correct only in a single-worker process.  Multiple workers will race on the
    state file and silently corrupt it.  See app/api/deps.py for details.
    """
    concurrency = int(os.environ.get("WEB_CONCURRENCY", "1"))
    worker_id = os.environ.get("GUNICORN_WORKER_ID") or os.environ.get("APP_WORKER_ID")
    if concurrency > 1 or worker_id not in (None, "0", ""):
        log.warning(
            "UNSAFE CONFIGURATION: DataSentinel is starting with WEB_CONCURRENCY=%s "
            "(worker_id=%s). The JSON/RLock state architecture is single-process only. "
            "Running multiple workers will cause silent state corruption. "
            "Use a single worker: uvicorn app.main:app --reload",
            concurrency,
            worker_id,
        )


def create_app() -> FastAPI:
    _warn_if_multi_worker()
    settings = get_settings()
    app = FastAPI(
        title="DataSentinel API",
        description="Autonomous Data Reliability Engineer: detect, investigate, remediate and validate silent data failures.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DataSentinelError)
    async def handle_domain_error(_: Request, exc: DataSentinelError) -> JSONResponse:
        log.warning("%s: %s", type(exc).__name__, exc.message)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health_router)
    app.include_router(router)
    return app


app = create_app()
