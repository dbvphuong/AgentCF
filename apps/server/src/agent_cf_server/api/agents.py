"""API routes for Agents and Agent Snapshots (AGN-003)."""

from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.agents.repository import AgentRepository
from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
)


class AgentCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    role_id: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=128)
    instructions: str = ""
    skill_ids: list[str] | None = None
    allowed_tool_ids: list[str] | None = None
    status: Literal["active", "archived"] = "active"


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    role_id: str | None = Field(default=None, min_length=1, max_length=128)
    model_id: str | None = Field(default=None, min_length=1, max_length=128)
    instructions: str | None = None
    skill_ids: list[str] | None = None
    allowed_tool_ids: list[str] | None = None
    status: Literal["active", "archived"] | None = None


def agents_router(repository: AgentRepository) -> APIRouter:
    router = APIRouter(prefix="/v1/agents", tags=["agents"])

    @router.get("", operation_id="listAgents")
    def list_agents(status_filter: str | None = Query(default=None, alias="status")) -> list[dict[str, Any]]:
        return repository.list_agents(status=status_filter)

    @router.post("", operation_id="createAgent", status_code=status.HTTP_201_CREATED)
    def create_agent(payload: AgentCreate) -> dict[str, Any]:
        try:
            return repository.create_agent(
                agent_id=payload.id,
                name=payload.name,
                role_id=payload.role_id,
                model_id=payload.model_id,
                instructions=payload.instructions,
                skill_ids=payload.skill_ids,
                allowed_tool_ids=payload.allowed_tool_ids,
                status=payload.status,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/{agent_id}", operation_id="getAgent")
    def get_agent(agent_id: str) -> dict[str, Any]:
        try:
            return repository.get_agent(agent_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/{agent_id}", operation_id="updateAgent")
    def update_agent(agent_id: str, payload: AgentUpdate) -> dict[str, Any]:
        try:
            return repository.update_agent(
                agent_id=agent_id,
                name=payload.name,
                role_id=payload.role_id,
                model_id=payload.model_id,
                instructions=payload.instructions,
                skill_ids=payload.skill_ids,
                allowed_tool_ids=payload.allowed_tool_ids,
                status=payload.status,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post("/{agent_id}/archive", operation_id="archiveAgent")
    def archive_agent(agent_id: str) -> dict[str, Any]:
        try:
            return repository.archive_agent(agent_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/{agent_id}/restore", operation_id="restoreAgent")
    def restore_agent(agent_id: str) -> dict[str, Any]:
        try:
            return repository.restore_agent(agent_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.delete("/{agent_id}", operation_id="deleteAgent", status_code=status.HTTP_204_NO_CONTENT)
    def delete_agent(agent_id: str) -> None:
        try:
            repository.delete_agent(agent_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Agent cần xóa. Tải lại danh sách và thử lại.") from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post("/{agent_id}/snapshot", operation_id="createAgentSnapshot", status_code=status.HTTP_201_CREATED)
    def create_agent_snapshot(agent_id: str) -> dict[str, Any]:
        try:
            return repository.create_agent_snapshot(agent_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return router
