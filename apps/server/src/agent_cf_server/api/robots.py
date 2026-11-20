"""API routes for Robots and Robot Versions (ROB-001)."""

from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.robots.repository import RobotRepository
from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
)


class RobotCreate(BaseModel):
    id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    active_version_id: str | None = None
    status: Literal["active", "archived"] = "active"


class RobotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    active_version_id: str | None = None
    status: Literal["active", "archived"] | None = None


class RobotVersionCreate(BaseModel):
    id: str | None = Field(default=None, max_length=128)
    entrypoint: str = Field(min_length=1)
    contract_version: str = Field(default="1.0.0", min_length=1, max_length=128)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    ready_to_use: bool = False


class RobotPublishRequest(BaseModel):
    bundle_sha256: str | None = None


def robots_router(repository: RobotRepository) -> APIRouter:
    router = APIRouter(prefix="/v1/robots", tags=["robots"])

    # -------------------------------------------------------------------------
    # Robots Catalog
    # -------------------------------------------------------------------------

    @router.get("", operation_id="listRobots")
    def list_robots(status_filter: str | None = Query(default=None, alias="status")) -> list[dict[str, Any]]:
        return repository.list_robots(status=status_filter)

    @router.post("", operation_id="createRobot", status_code=status.HTTP_201_CREATED)
    def create_robot(payload: RobotCreate) -> dict[str, Any]:
        try:
            return repository.create_robot(
                robot_id=payload.id,
                name=payload.name,
                description=payload.description,
                active_version_id=payload.active_version_id,
                status=payload.status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/{robot_id}", operation_id="getRobot")
    def get_robot(robot_id: str) -> dict[str, Any]:
        try:
            return repository.get_robot(robot_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.put("/{robot_id}", operation_id="updateRobot")
    def update_robot(robot_id: str, payload: RobotUpdate) -> dict[str, Any]:
        try:
            return repository.update_robot(
                robot_id=robot_id,
                name=payload.name,
                description=payload.description,
                active_version_id=payload.active_version_id,
                status=payload.status,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.delete("/{robot_id}", operation_id="deleteRobot", status_code=status.HTTP_204_NO_CONTENT)
    def delete_robot(robot_id: str) -> None:
        try:
            repository.delete_robot(robot_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Robot cần xóa. Tải lại danh sách và thử lại.") from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post("/{robot_id}/archive", operation_id="archiveRobot")
    def archive_robot(robot_id: str) -> dict[str, Any]:
        try:
            return repository.archive_robot(robot_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/{robot_id}/restore", operation_id="restoreRobot")
    def restore_robot(robot_id: str) -> dict[str, Any]:
        try:
            return repository.restore_robot(robot_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Robot Versions
    # -------------------------------------------------------------------------

    @router.get("/{robot_id}/versions", operation_id="listRobotVersions")
    def list_versions(robot_id: str) -> list[dict[str, Any]]:
        try:
            return repository.list_versions(robot_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/{robot_id}/versions", operation_id="createRobotVersion", status_code=status.HTTP_201_CREATED)
    def create_version(robot_id: str, payload: RobotVersionCreate) -> dict[str, Any]:
        try:
            return repository.create_draft_version(
                robot_id=robot_id,
                version_id=payload.id,
                entrypoint=payload.entrypoint,
                contract_version=payload.contract_version,
                input_schema=payload.input_schema,
                output_schema=payload.output_schema,
                ready_to_use=payload.ready_to_use,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/{robot_id}/versions/{version_id}", operation_id="getRobotVersion")
    def get_version(robot_id: str, version_id: str) -> dict[str, Any]:
        try:
            v = repository.get_version(version_id)
            if v.get("robot_id") != robot_id:
                raise ResourceNotFoundError(f"Version {version_id} not found for robot {robot_id}")
            return v
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/{robot_id}/versions/{version_id}/publish", operation_id="publishRobotVersion")
    def publish_version(robot_id: str, version_id: str, payload: RobotPublishRequest | None = None) -> dict[str, Any]:
        try:
            v = repository.get_version(version_id)
            if v.get("robot_id") != robot_id:
                raise ResourceNotFoundError(f"Version {version_id} not found for robot {robot_id}")
            bundle_hash = payload.bundle_sha256 if payload else None
            return repository.publish_version(version_id, bundle_sha256=bundle_hash)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    @router.get("/{robot_id}/statistics", operation_id="getRobotStatistics")
    def get_statistics(robot_id: str) -> dict[str, Any]:
        try:
            return repository.get_robot_statistics(robot_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return router
