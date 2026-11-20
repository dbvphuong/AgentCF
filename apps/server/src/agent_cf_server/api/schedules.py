"""HTTP API routes for Schedule management and execution (PROC-004)."""

from typing import Any
from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.processes.schedule_repository import ScheduleRepository
from agent_cf_server.infrastructure.runs.repository import ConflictError, IdempotencyConflict, RunRepository


class CreateScheduleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    process_version_id: str | None = Field(default=None, min_length=1, max_length=128)
    follow_current_configuration: bool = False
    cadence: str = Field(default="daily", pattern="^(manual|hourly|daily|weekly|cron)$")
    cron_expression: str | None = None
    timezone: str = "Asia/Ho_Chi_Minh"
    default_runner_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)


class TriggerScheduleRequest(BaseModel):
    scheduled_for: str = Field(description="RFC3339 UTC timestamp representing the scheduled tick")


def schedules_router(repository: ScheduleRepository, run_repository: RunRepository) -> APIRouter:
    router = APIRouter(tags=["schedules"])

    @router.get("/v1/processes/{process_id}/schedules", operation_id="listProcessSchedules")
    def list_process_schedules(process_id: str) -> dict[str, Any]:
        items = repository.list_schedules(process_id=process_id)
        return {"items": items}

    @router.post("/v1/processes/{process_id}/schedules", operation_id="createProcessSchedule", status_code=status.HTTP_201_CREATED)
    def create_process_schedule(
        process_id: str,
        payload: CreateScheduleRequest,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        project_id: str = Query(..., min_length=1),
    ) -> dict[str, Any]:
        try:
            return repository.create_schedule(
                project_id=project_id,
                process_id=process_id,
                process_version_id=payload.process_version_id,
                follow_current_configuration=payload.follow_current_configuration,
                name=payload.name,
                cadence=payload.cadence,
                cron_expression=payload.cron_expression,
                timezone_str=payload.timezone,
                default_runner_id=payload.default_runner_id,
                run_input=payload.input,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    @router.get("/v1/schedules/{schedule_id}", operation_id="getSchedule")
    def get_schedule(schedule_id: str) -> dict[str, Any]:
        try:
            return repository.get_schedule(schedule_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found") from exc

    @router.post("/v1/schedules/{schedule_id}/start", operation_id="startSchedule", status_code=status.HTTP_200_OK)
    def start_schedule(
        schedule_id: str,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        try:
            return repository.start_schedule(schedule_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found") from exc

    @router.post("/v1/schedules/{schedule_id}/stop", operation_id="stopSchedule", status_code=status.HTTP_200_OK)
    def stop_schedule(
        schedule_id: str,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        try:
            return repository.stop_schedule(schedule_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found") from exc

    @router.post("/v1/schedules/{schedule_id}/trigger", operation_id="triggerSchedule", status_code=status.HTTP_200_OK)
    def trigger_schedule(
        schedule_id: str,
        payload: TriggerScheduleRequest,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        try:
            return repository.trigger_schedule(
                schedule_id=schedule_id,
                scheduled_for=payload.scheduled_for,
                run_repo=run_repository,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found") from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return router
