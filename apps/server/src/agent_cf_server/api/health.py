"""Safe operational endpoints, separate from authenticated business APIs."""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DatabaseHealth(BaseModel):
    schema_version: int


class TemporalConfiguration(BaseModel):
    configured: bool


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    database: DatabaseHealth
    temporal: TemporalConfiguration


class ReadinessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    temporal: Literal["connected", "disabled"]


class HealthUnavailable(BaseModel):
    status: Literal["unavailable"] = "unavailable"
    component: Literal["database", "temporal"]


async def temporal_is_ready(settings) -> bool:
    from temporalio.client import Client

    async with asyncio.timeout(settings.request_timeout_seconds):
        client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )
        return await client.service_client.check_health()


def health_router(database, settings) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/healthz", operation_id="getHealth", response_model=HealthResponse,
        responses={503: {"model": HealthUnavailable}},
    )
    def health():
        try:
            state = database.health()
        except Exception:
            logger.exception("Business database health check failed")
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "component": "database"},
            )
        return HealthResponse(
            database=DatabaseHealth(schema_version=state["schema_version"]),
            temporal=TemporalConfiguration(configured=settings.temporal_enabled),
        )

    @router.get(
        "/readyz", operation_id="getReadiness", response_model=ReadinessResponse,
        responses={503: {"model": HealthUnavailable}},
    )
    async def readiness():
        # Run sqlite I/O off the ASGI loop, using a new connection per health call.
        try:
            await asyncio.to_thread(database.health)
        except Exception:
            logger.exception("Business database readiness check failed")
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "component": "database"},
            )
        if settings.temporal_enabled:
            try:
                ready = await temporal_is_ready(settings)
            except Exception:
                logger.warning("Temporal readiness check failed")
                ready = False
            if not ready:
                return JSONResponse(
                    status_code=503,
                    content={"status": "unavailable", "component": "temporal"},
                )
        return {"status": "ok", "temporal": "connected" if settings.temporal_enabled else "disabled"}

    return router
