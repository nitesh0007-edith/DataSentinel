"""HTTP API. Thin wrappers over DataSentinelService."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.api.deps import get_service
from app.core.models import Incident, IncidentType, PipelineRun
from app.pipeline.incident_injector import list_scenarios
from app.services.workflow import DataSentinelService

health_router = APIRouter(tags=["health"])
router = APIRouter(prefix="/api")


class GenerateRequest(BaseModel):
    rows: int | None = Field(default=None, ge=1000, le=1_000_000)
    seed: int | None = Field(default=None, ge=0)


class RunRequest(BaseModel):
    set_baseline: bool = False


class InjectRequest(BaseModel):
    type: IncidentType = IncidentType.FILTER_REGRESSION


@health_router.get("/health")
def health(svc: DataSentinelService = Depends(get_service)) -> dict[str, Any]:
    return {"status": "ok", "service": "datasentinel", "rca_engine": svc.rca_engine_label}


@router.get("/state", tags=["dashboard"])
def state(svc: DataSentinelService = Depends(get_service)) -> dict[str, Any]:
    return svc.dashboard()


@router.post("/demo/reset", tags=["demo"])
def reset_demo(req: GenerateRequest | None = None, svc: DataSentinelService = Depends(get_service)) -> dict[str, Any]:
    req = req or GenerateRequest()
    svc.reset_demo(req.rows, req.seed)
    return svc.dashboard()


@router.post("/data/generate", tags=["data"])
def generate(req: GenerateRequest | None = None, svc: DataSentinelService = Depends(get_service)) -> dict[str, Any]:
    req = req or GenerateRequest()
    return {"dataset": svc.generate_data(req.rows, req.seed).dataset}


@router.post("/pipeline/run", tags=["pipeline"])
def run(req: RunRequest | None = None, svc: DataSentinelService = Depends(get_service)) -> PipelineRun:
    return svc.run_pipeline(set_baseline=(req or RunRequest()).set_baseline)


@router.get("/pipeline/runs", tags=["pipeline"])
def runs(svc: DataSentinelService = Depends(get_service)) -> list[PipelineRun]:
    return svc.store.load().runs


@router.get("/incidents/types", tags=["incidents"])
def incident_types() -> list[dict[str, str]]:
    return list_scenarios()


@router.post("/incidents/inject", tags=["incidents"])
def inject(req: InjectRequest, svc: DataSentinelService = Depends(get_service)) -> dict[str, str]:
    return svc.inject(req.type)


@router.post("/incidents/detect", tags=["incidents"])
def detect(svc: DataSentinelService = Depends(get_service)) -> dict[str, Any]:
    return svc.detect()


@router.get("/incidents", tags=["incidents"])
def incidents(svc: DataSentinelService = Depends(get_service)) -> list[Incident]:
    return list(svc.store.load().incidents.values())


@router.get("/incidents/{incident_id}", tags=["incidents"])
def incident(incident_id: str, svc: DataSentinelService = Depends(get_service)) -> Incident:
    return svc.get_incident(incident_id)


@router.post("/incidents/{incident_id}/investigate", tags=["incidents"])
def investigate(incident_id: str, svc: DataSentinelService = Depends(get_service)) -> Incident:
    return svc.investigate(incident_id)


@router.post("/incidents/{incident_id}/fix", tags=["remediation"])
def fix(incident_id: str, svc: DataSentinelService = Depends(get_service)) -> Incident:
    return svc.propose_fix(incident_id)


@router.post("/incidents/{incident_id}/reject", tags=["remediation"])
def reject(incident_id: str, svc: DataSentinelService = Depends(get_service)) -> Incident:
    return svc.reject_fix(incident_id)


@router.post("/incidents/{incident_id}/apply", tags=["remediation"])
def apply(incident_id: str, svc: DataSentinelService = Depends(get_service)) -> Incident:
    return svc.apply_fix(incident_id)


@router.post("/incidents/{incident_id}/validate", tags=["validation"])
def validate(incident_id: str, svc: DataSentinelService = Depends(get_service)) -> Incident:
    return svc.validate(incident_id)


@router.get("/incidents/{incident_id}/report", tags=["reporting"], response_class=PlainTextResponse)
def report(incident_id: str, svc: DataSentinelService = Depends(get_service)) -> str:
    return svc.report_markdown(incident_id)
