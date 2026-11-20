"""HTTP API routes for Overview dashboard and Error Acknowledgment (OVW-001)."""

from typing import Any
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.overview.repository import OverviewRepository


class AcknowledgeErrorRequest(BaseModel):
    notes: str = Field(default="")
    acknowledged_by: str = Field(default="operator")


def overview_router(repository: OverviewRepository) -> APIRouter:
    router = APIRouter(tags=["overview"])

    @router.get("/v1/overview/summary", operation_id="getOverviewSummary")
    def get_overview_summary() -> dict[str, Any]:
        return repository.get_overview_summary()

    @router.post("/v1/runs/{run_id}/acknowledge-error", operation_id="acknowledgeRunError", status_code=status.HTTP_200_OK)
    def acknowledge_run_error(
        run_id: str,
        payload: AcknowledgeErrorRequest,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        try:
            return repository.acknowledge_error(
                run_id=run_id,
                acknowledged_by=payload.acknowledged_by,
                notes=payload.notes,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc

    return router
