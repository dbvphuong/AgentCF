"""API routes for Agents, Agent Templates, and Agent Snapshots (AGN-003)."""

from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.agents.repository import AgentRepository
from agent_cf_server.infrastructure.agents.template_repository import AgentTemplateRepository
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
    template_id: str | None = None
    allow_reply: bool = True
    allow_retry: bool = True
    allow_need_human: bool = True
    max_turns: int = Field(default=10, ge=1, le=50)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    role_id: str | None = Field(default=None, min_length=1, max_length=128)
    model_id: str | None = Field(default=None, min_length=1, max_length=128)
    instructions: str | None = None
    skill_ids: list[str] | None = None
    allowed_tool_ids: list[str] | None = None
    status: Literal["active", "archived"] | None = None
    template_id: str | None = None
    allow_reply: bool | None = None
    allow_retry: bool | None = None
    allow_need_human: bool | None = None
    max_turns: int | None = Field(default=None, ge=1, le=50)


class AgentTemplateCreate(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    prompt_text: str = Field(min_length=1)
    allow_reply: bool = True
    allow_retry: bool = True
    allow_need_human: bool = True
    max_turns: int = Field(default=10, ge=1, le=50)
    is_default: bool = False


class AgentTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    prompt_text: str | None = Field(default=None, min_length=1)
    allow_reply: bool | None = None
    allow_retry: bool | None = None
    allow_need_human: bool | None = None
    max_turns: int | None = Field(default=None, ge=1, le=50)
    is_default: bool | None = None


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
                template_id=payload.template_id,
                allow_reply=payload.allow_reply,
                allow_retry=payload.allow_retry,
                allow_need_human=payload.allow_need_human,
                max_turns=payload.max_turns,
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
                template_id=payload.template_id,
                allow_reply=payload.allow_reply,
                allow_retry=payload.allow_retry,
                allow_need_human=payload.allow_need_human,
                max_turns=payload.max_turns,
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


def agent_templates_router(repository: AgentTemplateRepository) -> APIRouter:
    router = APIRouter(prefix="/v1/agent-templates", tags=["agents"])

    @router.get("", operation_id="listAgentTemplates")
    def list_templates() -> list[dict[str, Any]]:
        return repository.list_templates()

    @router.post("", operation_id="createAgentTemplate", status_code=status.HTTP_201_CREATED)
    def create_template(payload: AgentTemplateCreate) -> dict[str, Any]:
        try:
            return repository.create_template(
                template_id=payload.id,
                name=payload.name,
                description=payload.description,
                prompt_text=payload.prompt_text,
                allow_reply=payload.allow_reply,
                allow_retry=payload.allow_retry,
                allow_need_human=payload.allow_need_human,
                max_turns=payload.max_turns,
                is_default=payload.is_default,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/{template_id}", operation_id="getAgentTemplate")
    def get_template(template_id: str) -> dict[str, Any]:
        try:
            return repository.get_template(template_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/{template_id}", operation_id="updateAgentTemplate")
    def update_template(template_id: str, payload: AgentTemplateUpdate) -> dict[str, Any]:
        try:
            return repository.update_template(
                template_id,
                name=payload.name,
                description=payload.description,
                prompt_text=payload.prompt_text,
                allow_reply=payload.allow_reply,
                allow_retry=payload.allow_retry,
                allow_need_human=payload.allow_need_human,
                max_turns=payload.max_turns,
                is_default=payload.is_default,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post("/{template_id}/default", operation_id="setDefaultAgentTemplate")
    def set_default_template(template_id: str) -> dict[str, Any]:
        try:
            return repository.set_default(template_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.delete("/{template_id}", operation_id="deleteAgentTemplate", status_code=status.HTTP_204_NO_CONTENT)
    def delete_template(template_id: str) -> None:
        try:
            repository.delete_template(template_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return router
