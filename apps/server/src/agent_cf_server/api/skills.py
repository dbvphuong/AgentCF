"""API routes for Skills, Tools, and Skill Versions (SKL-001, SKL-002)."""

from pathlib import Path
from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator

from agent_cf_server.domain.skills.local_source import validate_skill_source
from agent_cf_server.domain.skills.project_scope import validate_scope

from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from agent_cf_server.infrastructure.skills.repository import SkillRepository, sync_skills_from_directory


class ToolCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    tool_type: Literal["cli", "api", "internal"] = "internal"
    configuration: dict[str, Any] | None = None
    status: Literal["active", "archived"] = "active"


class ToolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    tool_type: Literal["cli", "api", "internal"] | None = None
    configuration: dict[str, Any] | None = None
    status: Literal["active", "archived"] | None = None


class SkillCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    status: Literal["active", "archived"] = "active"
    is_global: bool = False
    project_ids: list[str] = Field(default_factory=list)
    source_path: str | None = None
    source_runner_id: str | None = None

    @model_validator(mode="after")
    def validate_projects(self):
        validate_scope(self.is_global, self.project_ids)
        return self


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    status: Literal["active", "archived"] | None = None
    is_global: bool | None = None
    project_ids: list[str] | None = None
    source_path: str | None = None
    source_runner_id: str | None = None


class SkillVersionCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    instructions: str = ""
    source_path: str | None = None
    source_runner_id: str | None = None
    output_standards: str = ""
    tool_ids: list[str] | None = None

    @model_validator(mode="after")
    def validate_source(self):
        validate_skill_source(self.instructions, self.source_path, self.source_runner_id)
        return self


class SkillPublishRequest(BaseModel):
    bundle_sha256: str | None = None


class SkillDraftUpdate(BaseModel):
    instructions: str = ""
    source_path: str | None = None
    source_runner_id: str | None = None
    output_standards: str = ""
    tool_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source(self):
        validate_skill_source(self.instructions, self.source_path, self.source_runner_id)
        return self


class SkillSyncDirectoryRequest(BaseModel):
    directory_path: str = Field(min_length=1)
    is_global: bool = False
    project_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_projects(self):
        validate_scope(self.is_global, self.project_ids)
        return self


def skills_router(repository: SkillRepository) -> APIRouter:
    router = APIRouter(prefix="/v1/skills", tags=["skills"])

    # -------------------------------------------------------------------------
    # Tools
    # -------------------------------------------------------------------------
    @router.get("/tools", operation_id="listTools")
    def list_tools(status_filter: str | None = Query(default=None, alias="status")) -> list[dict[str, Any]]:
        return repository.list_tools(status=status_filter)

    @router.post("/tools", operation_id="createTool", status_code=status.HTTP_201_CREATED)
    def create_tool(payload: ToolCreate) -> dict[str, Any]:
        try:
            return repository.create_tool(
                tool_id=payload.id,
                name=payload.name,
                description=payload.description,
                tool_type=payload.tool_type,
                configuration=payload.configuration,
                status=payload.status,
            )
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/tools/{tool_id}", operation_id="getTool")
    def get_tool(tool_id: str) -> dict[str, Any]:
        try:
            return repository.get_tool(tool_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/tools/{tool_id}", operation_id="updateTool")
    def update_tool(tool_id: str, payload: ToolUpdate) -> dict[str, Any]:
        try:
            return repository.update_tool(
                tool_id=tool_id,
                name=payload.name,
                description=payload.description,
                tool_type=payload.tool_type,
                configuration=payload.configuration,
                status=payload.status,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post("/tools/{tool_id}/archive", operation_id="archiveTool")
    def archive_tool(tool_id: str) -> dict[str, Any]:
        try:
            return repository.archive_tool(tool_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/tools/{tool_id}/restore", operation_id="restoreTool")
    def restore_tool(tool_id: str) -> dict[str, Any]:
        try:
            return repository.restore_tool(tool_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.delete("/tools/{tool_id}", operation_id="deleteTool", status_code=status.HTTP_204_NO_CONTENT)
    def delete_tool(tool_id: str) -> None:
        try:
            repository.delete_tool(tool_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Tool cần xóa. Tải lại danh sách và thử lại.") from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Skills
    # -------------------------------------------------------------------------
    @router.get("", operation_id="listSkills", description="Skill catalog includes published_version_number (latest published, null if unavailable), latest_version_number and latest_version_status (latest draft or published). Existing Process/Run snapshots remain pinned.")
    def list_skills(status_filter: str | None = Query(default=None, alias="status"), project_id: str | None = None) -> list[dict[str, Any]]:
        return repository.list_skills(status=status_filter, project_id=project_id)

    @router.post("", operation_id="createSkill", status_code=status.HTTP_201_CREATED)
    def create_skill(payload: SkillCreate) -> dict[str, Any]:
        try:
            return repository.create_skill(
                skill_id=payload.id,
                name=payload.name,
                description=payload.description,
                status=payload.status,
                is_global=payload.is_global,
                project_ids=payload.project_ids,
                source_path=payload.source_path, source_runner_id=payload.source_runner_id,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/{skill_id}", operation_id="getSkill", description="Skill metadata includes published_version_number, latest_version_number and latest_version_status, nullable when no version exists. Published selection is separate from a newer draft and from pinned Process/Run history.")
    def get_skill(skill_id: str) -> dict[str, Any]:
        try:
            return repository.get_skill(skill_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/{skill_id}", operation_id="updateSkill")
    def update_skill(skill_id: str, payload: SkillUpdate) -> dict[str, Any]:
        try:
            return repository.update_skill(
                skill_id=skill_id,
                name=payload.name,
                description=payload.description,
                status=payload.status,
                is_global=payload.is_global,
                project_ids=payload.project_ids,
                source_path=payload.source_path, source_runner_id=payload.source_runner_id,
                update_source=bool({"source_path", "source_runner_id"} & payload.model_fields_set),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post("/{skill_id}/archive", operation_id="archiveSkill")
    def archive_skill(skill_id: str) -> dict[str, Any]:
        try:
            return repository.archive_skill(skill_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/{skill_id}/restore", operation_id="restoreSkill")
    def restore_skill(skill_id: str) -> dict[str, Any]:
        try:
            return repository.restore_skill(skill_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.delete("/{skill_id}", operation_id="deleteSkill", status_code=status.HTTP_204_NO_CONTENT)
    def delete_skill(skill_id: str) -> None:
        try:
            repository.delete_skill(skill_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Skill cần xóa. Tải lại danh sách và thử lại.") from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Skill Versions
    # -------------------------------------------------------------------------
    @router.get("/{skill_id}/versions", operation_id="listSkillVersions")
    def list_skill_versions(skill_id: str) -> list[dict[str, Any]]:
        return repository.list_versions(skill_id)

    @router.post("/{skill_id}/versions", operation_id="createSkillDraftVersion", status_code=status.HTTP_201_CREATED)
    def create_skill_draft_version(skill_id: str, payload: SkillVersionCreate) -> dict[str, Any]:
        try:
            return repository.create_draft_version(
                version_id=payload.id,
                skill_id=skill_id,
                instructions=payload.instructions,
                source_path=payload.source_path,
                source_runner_id=payload.source_runner_id,
                output_standards=payload.output_standards,
                tool_ids=payload.tool_ids,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/{skill_id}/versions/{version_id}", operation_id="getSkillVersion")
    def get_skill_version(skill_id: str, version_id: str) -> dict[str, Any]:
        try:
            ver = repository.get_version(version_id)
            if ver["skill_id"] != skill_id:
                raise ResourceNotFoundError(f"Version {version_id} does not belong to skill {skill_id}")
            return ver
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/{skill_id}/versions/{version_id}/publish", operation_id="publishSkillVersion")
    def publish_skill_version(
        skill_id: str, version_id: str, payload: SkillPublishRequest | None = None
    ) -> dict[str, Any]:
        try:
            ver = repository.get_version(version_id)
            if ver["skill_id"] != skill_id:
                raise ResourceNotFoundError(f"Version {version_id} does not belong to skill {skill_id}")
            bundle_sha = payload.bundle_sha256 if payload else None
            return repository.publish_version(version_id, bundle_sha256=bundle_sha)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/{skill_id}/versions/{version_id}", operation_id="updateSkillDraft")
    def update_skill_draft(skill_id: str, version_id: str, payload: SkillDraftUpdate) -> dict[str, Any]:
        try:
            version = repository.get_version(version_id)
            if version["skill_id"] != skill_id:
                raise ResourceNotFoundError("Skill version not found")
            return repository.update_draft_version(
                version_id, payload.instructions, payload.output_standards, payload.tool_ids,
                source_path=payload.source_path, source_runner_id=payload.source_runner_id,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.delete("/{skill_id}/versions/{version_id}", operation_id="deleteSkillDraftVersion", status_code=status.HTTP_204_NO_CONTENT)
    def delete_skill_draft_version(skill_id: str, version_id: str) -> None:
        try:
            ver = repository.get_version(version_id)
            if ver["skill_id"] != skill_id:
                raise ResourceNotFoundError(f"Version {version_id} does not belong to skill {skill_id}")
            repository.delete_draft_version(version_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phiên bản Skill cần xóa. Tải lại danh sách và thử lại.") from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Dynamic Directory Sync
    # -------------------------------------------------------------------------
    @router.post("/sync-directory", operation_id="syncSkillsDirectory")
    def sync_skills_directory(payload: SkillSyncDirectoryRequest) -> list[dict[str, Any]]:
        path = Path(payload.directory_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Directory not found: {path}")
        try:
            return sync_skills_from_directory(path, repository, is_global=payload.is_global, project_ids=payload.project_ids)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return router
