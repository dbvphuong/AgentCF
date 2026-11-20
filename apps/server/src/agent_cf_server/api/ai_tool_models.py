"""Local operator configuration of Codex/Antigravity models, separate from API models."""

from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_cf_server.infrastructure.settings.ai_tool_models import AiToolModelRepository
from agent_cf_server.infrastructure.settings.repository import ResourceNotFoundError, ResourceConflictError, InUseError


class AiToolModelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    model_identifier: str | None = Field(default=None, min_length=1, max_length=128)
    status: Literal["active", "disabled"] | None = None
    tool_id: Literal["codex", "antigravity"] | None = None

    @field_validator("name", "model_identifier", "status", "tool_id")
    @classmethod
    def validate_text(cls, value):
        if value is None or any(c in value for c in ("\0", "\n", "\r")):
            raise ValueError("Giá trị không hợp lệ")
        return value


class AiToolModelCreate(AiToolModelUpdate):
    id: str = Field(min_length=1, max_length=128)
    tool_id: Literal["codex", "antigravity"]
    name: str = Field(min_length=1, max_length=128)
    model_identifier: str = Field(min_length=1, max_length=128)
    status: Literal["active", "disabled"] = "active"


class AiToolModelConfigure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_id: Literal["codex", "antigravity"]
    active_model_ids: list[str] = Field(default_factory=list)


def ai_tool_models_router(repository: AiToolModelRepository):
    router = APIRouter(prefix="/v1/settings/ai-tool-models", tags=["settings"])

    def call(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ResourceNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except (ResourceConflictError, InUseError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.get("", operation_id="listAiToolModels")
    def list_models(tool_id: Literal["codex", "antigravity"] | None = None, status: Literal["active", "disabled"] | None = None):
        return repository.list(tool_id, status)

    @router.post("", operation_id="createAiToolModel", status_code=201)
    def create_model(payload: AiToolModelCreate):
        return call(repository.save, payload.id, payload.model_dump(exclude={"id"}), create=True)

    @router.post("/configure", operation_id="configureAiToolModels")
    def configure_tool_models(payload: AiToolModelConfigure):
        return call(repository.configure_tool_models, payload.tool_id, payload.active_model_ids)

    @router.post("/sync", operation_id="syncAiToolModels")
    def sync_models():
        return repository.sync_defaults()

    @router.get("/check", operation_id="checkAiToolModels")
    def check_tools():
        return repository.check_tools()

    @router.get("/{model_id}", operation_id="getAiToolModel")
    def get_model(model_id: str):
        return call(repository.get, model_id)

    @router.patch("/{model_id}", operation_id="updateAiToolModel")
    def update_model(model_id: str, payload: AiToolModelUpdate):
        return call(repository.save, model_id, payload.model_dump(exclude_unset=True))

    @router.delete("/{model_id}", operation_id="deleteAiToolModel", status_code=204)
    def delete_model(model_id: str):
        call(repository.delete, model_id)

    return router
