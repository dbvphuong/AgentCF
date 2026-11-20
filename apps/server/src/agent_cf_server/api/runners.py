"""API routes for Runner Pairing, Heartbeat, and PC Management (PC-001, CLI-001)."""

from typing import Any, Literal
from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_cf_server.infrastructure.runners.repository import (
    AuthenticationError,
    RunnerRepository,
    SessionInvalidError,
)
from agent_cf_server.infrastructure.settings.repository import ResourceConflictError, ResourceNotFoundError
from agent_cf_server.infrastructure.runners.file_browser import FileBrowser
from agent_cf_server.domain.skills.local_source import validate_absolute_path


class RunnerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=128)


class PairingCodeCreate(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    expires_in_seconds: int = Field(default=300, ge=30, le=86400)
    target_runner_id: str | None = None


class PairingExchangeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pairing_code: str = Field(min_length=1)
    machine_fingerprint: str | None = None
    client_version: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=128)
    device_id: str | None = Field(default=None, pattern=r"^device-[a-f0-9]{64}$")
    device_key: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$", repr=False, json_schema_extra={"writeOnly": True})


class SessionCreateRequest(BaseModel):
    client_version: str = Field(min_length=1)
    device_id: str | None = Field(default=None, pattern=r"^device-[a-f0-9]{64}$")
    device_key: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$", repr=False, json_schema_extra={"writeOnly": True})
    machine_fingerprint: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    os_name: str | None = Field(default=None, max_length=256)


class HeartbeatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    cpu_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    ram_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    running_attempts: list[str] = Field(default_factory=list)
    memory_total_bytes: int | None = Field(default=None, gt=0)
    memory_used_bytes: int | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def valid_memory(self):
        if self.memory_total_bytes is not None and self.memory_used_bytes is not None and self.memory_used_bytes > self.memory_total_bytes:
            raise ValueError('RAM đã dùng không thể vượt tổng RAM')
        return self


class SkillFilesRequest(BaseModel):
    path: str | None = Field(default=None, max_length=4096)


class SkillFileEntry(BaseModel):
    name: str = Field(min_length=1, max_length=4096)
    path: str = Field(min_length=1, max_length=4096)
    is_dir: bool


class SkillDirectoryResult(BaseModel):
    path: str | None = Field(default=None, max_length=4096)
    parent: str | None = Field(default=None, max_length=4096)
    roots: list[str] = Field(default_factory=list, max_length=26)
    entries: list[SkillFileEntry] = Field(default_factory=list, max_length=500)
    truncated: bool = False
    error: str | None = Field(default=None, max_length=8192)

    @model_validator(mode="after")
    def validate_directory(self):
        if not self.error and (not self.path or not self.parent):
            raise ValueError("Cần thư mục kết quả hoặc thông báo lỗi")
        return self


class SkillFilesResult(BaseModel):
    session_id: str = Field(min_length=1)
    result: SkillDirectoryResult


def runners_router(repository: RunnerRepository) -> APIRouter:
    router = APIRouter(tags=["runners"])
    file_browser = FileBrowser()

    @router.post("/v1/runners/{runner_id}/skill-files", operation_id="browseSkillFiles", status_code=201)
    def browse_skill_files(runner_id: str, payload: SkillFilesRequest):
        try:
            runner = repository.get_runner(runner_id)
            if runner["deleted_at"] or runner["status"] == "disabled":
                raise HTTPException(409, "PC không khả dụng")
            if payload.path:
                validate_absolute_path(payload.path)
            return file_browser.create(runner_id, payload.path or None)
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/v1/runners/{runner_id}/skill-files/{request_id}", operation_id="getSkillFiles")
    def get_skill_files(runner_id: str, request_id: str):
        try:
            runner = repository.get_runner(runner_id)
            if runner["deleted_at"] or runner["status"] == "disabled":
                raise HTTPException(409, "PC không khả dụng")
            return file_browser.get(runner_id, request_id)
        except (KeyError, ResourceNotFoundError) as exc:
            raise HTTPException(404, "Yêu cầu chọn file đã hết hạn; mở lại để thử") from exc

    @router.post("/v1/runners/{runner_id}/skill-files/{request_id}/result", operation_id="completeSkillFiles", status_code=204)
    def complete_skill_files(runner_id: str, request_id: str, payload: SkillFilesResult, authorization: str | None = Header(default=None)):
        try:
            if not authorization or not authorization.startswith("Bearer "):
                raise AuthenticationError("Missing Bearer token")
            repository.authenticate_runner(runner_id, authorization[7:])
            repository.require_active_session(runner_id, payload.session_id)
            result = payload.result.model_dump()
            if len(str(result)) > 256_000:
                raise HTTPException(422, "Danh sách file quá lớn")
            file_browser.complete(runner_id, request_id, result)
        except AuthenticationError as exc:
            raise HTTPException(401, str(exc)) from exc
        except SessionInvalidError as exc:
            raise HTTPException(403, str(exc)) from exc
        except (KeyError, ResourceNotFoundError) as exc:
            raise HTTPException(404, "Không tìm thấy yêu cầu chọn file") from exc

    # -------------------------------------------------------------------------
    # Pairing Codes
    # -------------------------------------------------------------------------
    @router.post("/v1/pairing-codes", operation_id="createPairingCode", status_code=status.HTTP_201_CREATED)
    def create_pairing_code(payload: PairingCodeCreate) -> dict[str, Any]:
        try:
            raw_code, record = repository.create_pairing_code(
                workspace_id=payload.workspace_id,
                name=payload.name,
                expires_in_seconds=payload.expires_in_seconds,
                target_runner_id=payload.target_runner_id,
            )
            return {
                "pairing_code": raw_code,
                "id": record["id"],
                "expires_at": record["expires_at"],
                "name": record["name"],
            }
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/v1/pairing-codes/inspect", operation_id="inspectPairingCode")
    def inspect_pairing_code(payload: PairingExchangeRequest):
        try:
            return repository.inspect_pairing_code(payload.pairing_code)
        except AuthenticationError as exc:
            raise HTTPException(401, str(exc)) from exc

    @router.get("/v1/pairing-codes/{pairing_id}", operation_id="getPairingState")
    def pairing_state(pairing_id: str):
        try:
            return repository.pairing_state(pairing_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.post("/v1/runners/pair", operation_id="pairRunner", status_code=status.HTTP_201_CREATED)
    def pair_runner(payload: PairingExchangeRequest) -> dict[str, Any]:
        try:
            raw_token, runner = repository.exchange_pairing_code(
                raw_code=payload.pairing_code,
                machine_fingerprint=payload.machine_fingerprint,
                client_version=payload.client_version,
                name=payload.name,
                device_id=payload.device_id,
                device_key=payload.device_key,
            )
            return {
                "runner_id": runner["id"],
                "runner_token": raw_token,
                "runner": runner,
            }
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        except ResourceConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.post("/v1/runners/{runner_id}/disconnect", operation_id="disconnectRunner", status_code=204)
    def disconnect_runner(runner_id: str):
        try:
            repository.disconnect_runner(runner_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(409, str(exc)) from exc

    # -------------------------------------------------------------------------
    # PC List & Details (Operator)
    # -------------------------------------------------------------------------
    @router.get("/v1/runners", operation_id="listRunners")
    def list_runners(
        workspace_id: str | None = Query(default=None),
        status_filter: str | None = Query(default=None, alias="status"),
    ) -> list[dict[str, Any]]:
        return repository.list_runners(workspace_id=workspace_id, status=status_filter)

    @router.get("/v1/runners/{runner_id}", operation_id="getRunner")
    def get_runner(runner_id: str) -> dict[str, Any]:
        try:
            return repository.get_runner(runner_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/v1/runners/{runner_id}/disable", operation_id="disableRunner")
    def disable_runner(runner_id: str) -> dict[str, Any]:
        try:
            return repository.disable_runner(runner_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/v1/runners/{runner_id}", operation_id="updateRunner")
    def update_runner(runner_id: str, payload: RunnerUpdate):
        try:
            return repository.rename_runner(runner_id, payload.name)
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.delete("/v1/runners/{runner_id}", operation_id="removeRunner", status_code=204)
    def remove_runner(runner_id: str):
        try:
            repository.remove_runner(runner_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/v1/runners/{runner_id}/enable", operation_id="enableRunner")
    def enable_runner(runner_id: str) -> dict[str, Any]:
        try:
            return repository.enable_runner(runner_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/v1/runners/{runner_id}/revoke", operation_id="revokeRunner", status_code=status.HTTP_204_NO_CONTENT)
    def revoke_runner(runner_id: str) -> None:
        try:
            repository.revoke_runner(runner_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Runner Execution Sessions & Heartbeats
    # -------------------------------------------------------------------------
    @router.post("/v1/runners/{runner_id}/sessions", operation_id="createRunnerSession", status_code=status.HTTP_201_CREATED)
    def create_runner_session(
        runner_id: str,
        payload: SessionCreateRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Bearer token")
        token = authorization[len("Bearer ") :]
        try:
            repository.authenticate_runner(runner_id, token)
            return repository.create_session(
                runner_id=runner_id,
                client_version=payload.client_version,
                machine_fingerprint=payload.machine_fingerprint,
                capabilities=payload.capabilities,
                device_id=payload.device_id,
                device_key=payload.device_key,
                os_name=payload.os_name,
            )
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.delete("/v1/runners/{runner_id}/sessions/{session_id}", operation_id="closeRunnerSession", status_code=204)
    def close_session(runner_id: str, session_id: str, authorization: str | None = Header(default=None)):
        try:
            if not authorization or not authorization.startswith("Bearer "):
                raise AuthenticationError("Missing Bearer token")
            repository.authenticate_runner(runner_id, authorization[7:])
            repository.close_session(runner_id, session_id)
        except AuthenticationError as exc:
            raise HTTPException(401, str(exc)) from exc
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/v1/runners/{runner_id}/heartbeat", operation_id="runnerHeartbeat")
    def runner_heartbeat(
        runner_id: str,
        payload: HeartbeatRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Bearer token")
        token = authorization[len("Bearer ") :]
        try:
            repository.authenticate_runner(runner_id, token)
            result = repository.heartbeat(
                runner_id=runner_id,
                session_id=payload.session_id,
                cpu_percent=payload.cpu_percent,
                ram_percent=payload.ram_percent,
                memory_total_bytes=payload.memory_total_bytes,
                memory_used_bytes=payload.memory_used_bytes,
                running_attempts=payload.running_attempts,
            )
            if not result["stop_requested"]:
                result["skill_file_requests"] = file_browser.pending(runner_id)
            return result
        except AuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        except SessionInvalidError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return router
