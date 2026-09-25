"""FastAPI application entrypoint: ``uvicorn app.main:app --reload`` from backend/."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health_router, router
from app.core.config import get_settings
from app.core.errors import DataSentinelError
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("api")


def create_app() -> FastAPI:
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
