"""HTTP API routes for Runs, Tasks, Attempts, and Artifacts (RUN-002, RUN-003, REL-001, REL-003)."""

import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.runs.repository import (
    AuthenticationError,
    ConflictError,
    IdempotencyConflict,
    RunRepository,
)


class CreateRunRequest(BaseModel):
    process_version_id: str = Field(min_length=1, max_length=128)
    input: dict[str, Any] = Field(default_factory=dict)
    default_runner_id: str | None = Field(default=None, max_length=128)


class CreateCurrentRunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    default_runner_id: str | None = None


class CancelRequest(BaseModel):
    reason: str = Field(default="Operator cancelled")


class ClaimRequestBody(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    lease_seconds: int = Field(default=60, ge=10, le=3600)


class CompleteRequestBody(BaseModel):
    session_id: str | None = None
    generation: int | None = None
    outcome: str = Field(pattern="^(succeeded|failed|cancelled)$")
    process_stopped: bool = True
    exit_code: int = 0
    output: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    process: dict[str, Any] | None = None


class RegisterArtifactRequest(BaseModel):
    logical_name: str = Field(min_length=1, max_length=256)
    media_type: str = Field(default="text/plain", min_length=1, max_length=128)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern="^[a-f0-9]{64}$")


class ContinueRunRequest(BaseModel):
    task_id: str | None = None
    decision: str = "proceed"
    feedback: str = ""
    input: dict[str, Any] | None = None


class RecordObservationRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    observation_type: str = Field(default="process_evidence", min_length=1, max_length=64)
    data: dict[str, Any] = Field(default_factory=dict)


def runs_router(repository: RunRepository, artifacts_dir: Path) -> APIRouter:
    router = APIRouter(tags=["runs"])

    @router.post("/v1/processes/{process_id}/runs", operation_id="createCurrentProcessRun", status_code=202)
    def create_current_run(process_id: str, payload: CreateCurrentRunRequest, idempotency_key: str = Header(...,alias="Idempotency-Key")):
        try:
            created = repository.create_from_version(process_id=process_id, run_input=payload.input, default_runner_id=payload.default_runner_id, principal_id="operator", request_key=idempotency_key, request_sha256=hashlib.sha256(json.dumps(payload.model_dump(),sort_keys=True).encode()).hexdigest())
            return repository.get(created["run_id"])
        except KeyError as exc:
            raise HTTPException(404,"Không tìm thấy Process hoặc cấu hình liên quan") from exc
        except IdempotencyConflict as exc:
            raise HTTPException(409,"idempotency_conflict") from exc
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @router.get("/v1/process-versions/{version_id}/run-context", operation_id="getRunContext", description="Read-only launch context from the pinned published snapshot. Returns topic_supported, working_directory and runner_id for local Skill nodes sharing one PC/root, otherwise a reason. Create Run input accepts topic_directory plus optional request; Server derives topic from the folder name, validates it within the pinned root, and Client verifies that the directory exists. Cwd and Skill workflows are preserved; no folder is created by this API.")
    def run_context(version_id: str):
        try:
            return repository.run_context(version_id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    # -------------------------------------------------------------------------
    # Runs (Operator)
    # -------------------------------------------------------------------------
    @router.post("/v1/runs", operation_id="createRun", status_code=status.HTTP_202_ACCEPTED)
    def create_run(
        payload: CreateRunRequest,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = "operator"
        raw_body = json.dumps(payload.model_dump(), sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        try:
            created = repository.create_from_version(
                version_id=payload.process_version_id,
                run_input=payload.input,
                principal_id=principal_id,
                request_key=idempotency_key,
                request_sha256=request_sha256,
                default_runner_id=payload.default_runner_id,
            )
            return repository.get(created["run_id"])
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_conflict") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    @router.get("/v1/runs", operation_id="listRuns")
    def list_runs(
        project_id: str | None = Query(default=None),
        process_id: str | None = Query(default=None),
        status_filter: str | None = Query(default=None, alias="status"),
        cursor: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        search: str | None = Query(default=None, max_length=128),
        started_from: datetime | None = Query(default=None),
        started_to: datetime | None = Query(default=None),
    ) -> dict[str, Any]:
        statuses = [s.strip() for s in status_filter.split(",")] if status_filter else None
        if any(value is not None and value.tzinfo is None for value in (started_from, started_to)):
            raise HTTPException(422, "Date filters require a timezone")
        start = started_from.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if started_from else None
        end = started_to.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if started_to else None
        items, next_cursor = repository.list_runs(
            project_id=project_id,
            process_id=process_id,
            status_filter=statuses,
            cursor=cursor,
            limit=limit,
            search=search,
            started_from=start,
            started_to=end,
        )
        total = repository.count_runs(project_id=project_id, process_id=process_id, status_filter=statuses, search=search, started_from=start, started_to=end)
        total_all = repository.count_runs(project_id=project_id)
        return {"items": items, "next_cursor": next_cursor, "total": total, "total_all": total_all}

    @router.get("/v1/runs/{run_id}", operation_id="getRun")
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return repository.get(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc

    @router.post("/v1/runs/{run_id}/cancel", operation_id="cancelRun", status_code=status.HTTP_202_ACCEPTED)
    def cancel_run(
        run_id: str,
        payload: CancelRequest,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        principal_id = "operator"
        raw_body = json.dumps(payload.model_dump(), sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        try:
            return repository.cancel_run(
                run_id=run_id,
                principal_id=principal_id,
                request_key=idempotency_key,
                request_sha256=request_sha256,
                reason=payload.reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_conflict") from exc

    @router.post("/v1/runs/{run_id}/continue", operation_id="continueRun", status_code=status.HTTP_200_OK)
    def continue_run(
        run_id: str,
        payload: ContinueRunRequest,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = "operator"
        raw_body = json.dumps(payload.model_dump(), sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        try:
            return repository.continue_run(
                run_id=run_id,
                principal_id=principal_id,
                decision=payload.decision,
                task_id=payload.task_id,
                feedback=payload.feedback,
                input_data=payload.input,
                request_key=idempotency_key,
                request_sha256=request_sha256,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_conflict") from exc

    @router.get("/v1/runs/{run_id}/events", operation_id="getRunEvents")
    def get_run_events(
        run_id: str,
        cursor: int | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        items, next_cursor = repository.get_run_events(run_id, cursor=cursor, limit=limit)
        return {"items": items, "next_cursor": next_cursor}

    # -------------------------------------------------------------------------
    # Runner Work & Task Claiming
    # -------------------------------------------------------------------------
    @router.get("/v1/runners/{runner_id}/work", operation_id="listRunnerWork")
    def list_runner_work(
        runner_id: str,
        session_id: str = Query(..., min_length=1),
    ) -> dict[str, Any]:
        items = repository.list_work(runner_id=runner_id, session_id=session_id)
        return {"items": items}

    @router.post("/v1/task-runs/{task_run_id}/claim", operation_id="claimTaskRun", status_code=status.HTTP_201_CREATED)
    def claim_task_run(
        task_run_id: str,
        payload: ClaimRequestBody,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        authorization: str = Header(..., alias="Authorization"),
    ) -> dict[str, Any]:
        # Extract runner token from Bearer auth
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")

        # Look up runner by checking session
        with repository.database.connect() as conn:
            row = conn.execute("SELECT runner_id FROM runner_sessions WHERE id=?", (payload.session_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
            runner_id = row["runner_id"]

        raw_body = json.dumps(payload.model_dump(), sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        try:
            return repository.claim_task_run(
                task_run_id=task_run_id,
                runner_id=runner_id,
                session_id=payload.session_id,
                request_key=idempotency_key,
                request_sha256=request_sha256,
                lease_seconds=payload.lease_seconds,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TaskRun not found") from exc
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_conflict") from exc

    @router.post("/v1/attempts/{attempt_id}/complete", operation_id="completeAttempt")
    def complete_attempt(
        attempt_id: str,
        payload: CompleteRequestBody,
        execution_token: str = Header(..., alias="X-Execution-Token"),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        raw_body = json.dumps(payload.model_dump(), sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        try:
            return repository.complete_attempt(
                attempt_id=attempt_id,
                execution_token=execution_token,
                outcome=payload.outcome,
                process_stopped=payload.process_stopped,
                exit_code=payload.exit_code,
                output=payload.output,
                error=payload.error,
                artifact_ids=payload.artifact_ids,
                process_evidence=payload.process,
                request_key=idempotency_key,
                request_sha256=request_sha256,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found") from exc
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_conflict") from exc

    @router.post("/v1/attempts/{attempt_id}/observations", operation_id="recordAttemptObservation", status_code=status.HTTP_202_ACCEPTED)
    def record_attempt_observation(
        attempt_id: str,
        payload: RecordObservationRequest,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        authorization: str = Header(..., alias="Authorization"),
    ) -> dict[str, Any]:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")

        with repository.database.connect() as conn:
            row = conn.execute("SELECT runner_id FROM runner_sessions WHERE id=?", (payload.session_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
            runner_id = row["runner_id"]

        raw_body = json.dumps(payload.model_dump(), sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        try:
            return repository.record_attempt_observation(
                attempt_id=attempt_id,
                runner_id=runner_id,
                session_id=payload.session_id,
                observation_type=payload.observation_type,
                data=payload.data,
                request_key=idempotency_key,
                request_sha256=request_sha256,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found") from exc
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_conflict") from exc

    # -------------------------------------------------------------------------
    # Artifacts
    # -------------------------------------------------------------------------
    @router.post("/v1/attempts/{attempt_id}/artifacts", operation_id="registerArtifact", status_code=status.HTTP_201_CREATED)
    def register_artifact(
        attempt_id: str,
        payload: RegisterArtifactRequest,
        execution_token: str = Header(..., alias="X-Execution-Token"),
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        raw_body = json.dumps(payload.model_dump(), sort_keys=True)
        request_sha256 = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()

        try:
            return repository.register_artifact(
                attempt_id=attempt_id,
                execution_token=execution_token,
                logical_name=payload.logical_name,
                media_type=payload.media_type,
                size_bytes=payload.size_bytes,
                sha256=payload.sha256,
                request_key=idempotency_key,
                request_sha256=request_sha256,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found") from exc
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_conflict") from exc

    @router.put("/v1/artifacts/{artifact_id}/content", operation_id="uploadArtifact")
    async def upload_artifact(
        artifact_id: str,
        request: Request,
        execution_token: str = Header(..., alias="X-Execution-Token"),
    ) -> dict[str, Any]:
        content = await request.body()
        try:
            return repository.save_artifact_content(
                artifact_id=artifact_id,
                execution_token=execution_token,
                content=content,
                storage_dir=artifacts_dir,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found") from exc
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    @router.get("/v1/artifacts/{artifact_id}/content", operation_id="downloadArtifact")
    def download_artifact(artifact_id: str) -> Response:
        try:
            art, content = repository.get_artifact(artifact_id=artifact_id, storage_dir=artifacts_dir)
            return Response(content=content, media_type=art["media_type"])
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found") from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact content not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return router
