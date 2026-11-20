"""API routes for Settings, Providers, Models, Roles, and Runtime Inventory (SET-001, SET-002)."""

from typing import Any, Literal
from urllib.parse import urlsplit
import httpx
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from agent_cf_server.infrastructure.settings.inventory import load_runtime_inventory
from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
    SettingsRepository,
)


class ProviderCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    api_format: Literal["openai", "anthropic", "google", "custom"]
    base_url: str = Field(min_length=1)
    api_key: str | None = None
    request_timeout_seconds: int = Field(default=60, ge=1, le=300)
    status: Literal["active", "disabled"] = "active"


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    api_format: Literal["openai", "anthropic", "google", "custom"] | None = None
    base_url: str | None = Field(default=None, min_length=1)
    api_key: str | None = None
    request_timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    status: Literal["active", "disabled"] | None = None


class ProviderTestRequest(BaseModel):
    base_url: str | None = None
    api_format: Literal["openai", "anthropic", "google", "custom"] = "custom"
    api_key: str | None = None
    request_timeout_seconds: int = Field(default=30, ge=1, le=300)
    provider_id: str | None = None
    model: str | None = None


class ModelCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    provider_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    model_identifier: str = Field(min_length=1, max_length=128)
    max_output_tokens: int | None = Field(default=None, gt=0)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    status: Literal["active", "disabled"] = "active"
    runtime_adapter: Literal["codex", "antigravity"] | None = Field(default=None, json_schema_extra={"deprecated": True}, description="Legacy compatibility only; CLI models use /v1/settings/ai-tool-models.")


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    model_identifier: str | None = Field(default=None, min_length=1, max_length=128)
    max_output_tokens: int | None = Field(default=None, gt=0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    status: Literal["active", "disabled"] | None = None
    runtime_adapter: Literal["codex", "antigravity"] | None = Field(default=None, json_schema_extra={"deprecated": True}, description="Legacy compatibility only; CLI models use /v1/settings/ai-tool-models.")


class RoleCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    status: Literal["active", "archived"] = "active"


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    status: Literal["active", "archived"] | None = None


class GeneralSettingsUpdate(BaseModel):
    default_task_timeout_seconds: int | None = Field(default=None, ge=10, le=86400)
    default_logs_lines: int | None = Field(default=None, ge=10, le=10000)
    default_timezone: str | None = None


def settings_router(repository: SettingsRepository) -> APIRouter:
    router = APIRouter(prefix="/v1/settings", tags=["settings"])

    # -------------------------------------------------------------------------
    # SET-001: Runtime Inventory
    # -------------------------------------------------------------------------
    @router.get("/runtime-inventory", operation_id="getRuntimeInventory")
    def get_runtime_inventory() -> dict[str, Any]:
        try:
            inventory = load_runtime_inventory()
            return inventory.to_dict()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Providers
    # -------------------------------------------------------------------------
    @router.get("/providers", operation_id="listProviders")
    def list_providers(status_filter: str | None = Query(default=None, alias="status")) -> list[dict[str, Any]]:
        return repository.list_providers(status=status_filter)

    @router.post("/providers", operation_id="createProvider", status_code=status.HTTP_201_CREATED)
    def create_provider(payload: ProviderCreate) -> dict[str, Any]:
        try:
            return repository.create_provider(
                provider_id=payload.id,
                name=payload.name,
                api_format=payload.api_format,
                base_url=payload.base_url,
                api_key=payload.api_key,
                request_timeout_seconds=payload.request_timeout_seconds,
                status=payload.status,
            )
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/providers/{provider_id}", operation_id="getProvider")
    def get_provider(provider_id: str) -> dict[str, Any]:
        try:
            return repository.get_provider(provider_id, include_secret=True)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/providers/{provider_id}", operation_id="updateProvider")
    def update_provider(provider_id: str, payload: ProviderUpdate) -> dict[str, Any]:
        try:
            return repository.update_provider(
                provider_id=provider_id,
                name=payload.name,
                api_format=payload.api_format,
                base_url=payload.base_url,
                api_key=payload.api_key,
                request_timeout_seconds=payload.request_timeout_seconds,
                status=payload.status,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    def _test_connection_endpoint(
        base_url: str,
        api_format: str,
        api_key: str | None = None,
        timeout_seconds: int = 60,
        model: str | None = None,
    ) -> dict[str, Any]:
        url = base_url.rstrip("/")
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HTTPException(422, "Base URL must be an HTTP(S) endpoint without credentials, query, or fragment")
        headers = {"Accept": "application/json"}
        if api_key:
            if api_format == "anthropic":
                headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
            elif api_format == "google":
                headers["x-goog-api-key"] = api_key
            else:
                headers["Authorization"] = f"Bearer {api_key}"

        # If a model is specified (e.g. qwen-code), test chat completion directly with a ping message
        if model and api_format in ("openai", "custom"):
            try:
                with httpx.Client(timeout=timeout_seconds, follow_redirects=False, trust_env=False) as client:
                    chat_url = url + "/chat/completions"
                    chat_body = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}
                    res = client.post(chat_url, headers={**headers, "Content-Type": "application/json"}, json=chat_body)
                    code = res.status_code
                    return {"reachable": True, "ok": 200 <= code < 300, "http_status": code, "model": model}
            except httpx.TimeoutException:
                return {"reachable": False, "ok": False, "error": "timeout"}
            except httpx.HTTPError:
                return {"reachable": False, "ok": False, "error": "connection_failed"}

        # Probe endpoints: for openai/custom, check /models first, then fallback to base url
        endpoints = [url + "/models", url] if api_format in ("openai", "custom") else [url if api_format == "custom" else url + "/models"]
        last_code = 0
        try:
            with httpx.Client(timeout=timeout_seconds, follow_redirects=False, trust_env=False) as client:
                for endpoint in endpoints:
                    with client.stream("GET", endpoint, headers=headers) as response:
                        last_code = response.status_code
                        if 200 <= last_code < 300:
                            return {"reachable": True, "ok": True, "http_status": last_code}
                return {"reachable": True, "ok": 200 <= last_code < 300, "http_status": last_code}
        except httpx.TimeoutException:
            return {"reachable": False, "ok": False, "error": "timeout"}
        except httpx.HTTPError:
            return {"reachable": False, "ok": False, "error": "connection_failed"}

    @router.post("/providers/{provider_id}/test", operation_id="testProviderConnection")
    def test_provider_connection(provider_id: str) -> dict[str, Any]:
        try:
            provider = repository.get_provider(provider_id, include_secret=True)
        except ResourceNotFoundError as exc:
            raise HTTPException(404, "Provider not found") from exc
        key = provider.get("api_key") or provider.get("api_key_ciphertext")
        return _test_connection_endpoint(
            base_url=provider["base_url"],
            api_format=provider["api_format"],
            api_key=key,
            timeout_seconds=provider.get("request_timeout_seconds", 60),
        )

    @router.post("/providers-test", operation_id="testProviderDirect")
    def test_provider_direct(payload: ProviderTestRequest) -> dict[str, Any]:
        base_url = payload.base_url
        key = payload.api_key
        api_format = payload.api_format
        timeout = payload.request_timeout_seconds
        if payload.provider_id:
            try:
                p = repository.get_provider(payload.provider_id, include_secret=True)
                base_url = base_url or p.get("base_url")
                key = key or p.get("api_key") or p.get("api_key_ciphertext")
                if not payload.base_url:
                    api_format = p.get("api_format", api_format)
                timeout = timeout or p.get("request_timeout_seconds", 30)
            except ResourceNotFoundError:
                pass
        if not base_url:
            raise HTTPException(422, "Base URL is required")
        return _test_connection_endpoint(
            base_url=base_url,
            api_format=api_format,
            api_key=key,
            timeout_seconds=timeout,
            model=payload.model,
        )

    @router.delete("/providers/{provider_id}", operation_id="deleteProvider", status_code=status.HTTP_204_NO_CONTENT)
    def delete_provider(provider_id: str) -> None:
        try:
            repository.delete_provider(provider_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Provider cần xóa. Tải lại danh sách và thử lại.") from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Models
    # -------------------------------------------------------------------------
    @router.get("/models", operation_id="listModels")
    def list_models(
        provider_id: str | None = Query(default=None),
        status_filter: str | None = Query(default=None, alias="status"),
    ) -> list[dict[str, Any]]:
        return repository.list_models(provider_id=provider_id, status=status_filter)

    @router.post("/models", operation_id="createModel", status_code=status.HTTP_201_CREATED)
    def create_model(payload: ModelCreate) -> dict[str, Any]:
        try:
            return repository.create_model(
                model_id=payload.id,
                provider_id=payload.provider_id,
                name=payload.name,
                model_identifier=payload.model_identifier,
                runtime_adapter=payload.runtime_adapter,
                max_output_tokens=payload.max_output_tokens,
                temperature=payload.temperature,
                status=payload.status,
            )
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/models/{model_id}", operation_id="getModel")
    def get_model(model_id: str) -> dict[str, Any]:
        try:
            return repository.get_model(model_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/models/{model_id}", operation_id="updateModel")
    def update_model(model_id: str, payload: ModelUpdate) -> dict[str, Any]:
        try:
            return repository.update_model(
                model_id=model_id,
                name=payload.name,
                model_identifier=payload.model_identifier,
                runtime_adapter=payload.runtime_adapter,
                update_runtime="runtime_adapter" in payload.model_fields_set,
                max_output_tokens=payload.max_output_tokens,
                temperature=payload.temperature,
                status=payload.status,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.delete("/models/{model_id}", operation_id="deleteModel", status_code=status.HTTP_204_NO_CONTENT)
    def delete_model(model_id: str) -> None:
        try:
            repository.delete_model(model_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Model API cần xóa. Tải lại danh sách và thử lại.") from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # Roles
    # -------------------------------------------------------------------------
    @router.get("/roles", operation_id="listRoles")
    def list_roles(status_filter: str | None = Query(default=None, alias="status")) -> list[dict[str, Any]]:
        return repository.list_roles(status=status_filter)

    @router.post("/roles", operation_id="createRole", status_code=status.HTTP_201_CREATED)
    def create_role(payload: RoleCreate) -> dict[str, Any]:
        try:
            return repository.create_role(
                role_id=payload.id,
                name=payload.name,
                description=payload.description,
                status=payload.status,
            )
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.get("/roles/{role_id}", operation_id="getRole")
    def get_role(role_id: str) -> dict[str, Any]:
        try:
            return repository.get_role(role_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.patch("/roles/{role_id}", operation_id="updateRole")
    def update_role(role_id: str, payload: RoleUpdate) -> dict[str, Any]:
        try:
            return repository.update_role(
                role_id=role_id,
                name=payload.name,
                description=payload.description,
                status=payload.status,
            )
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ResourceConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.post("/roles/{role_id}/archive", operation_id="archiveRole")
    def archive_role(role_id: str) -> dict[str, Any]:
        try:
            return repository.archive_role(role_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/roles/{role_id}/restore", operation_id="restoreRole")
    def restore_role(role_id: str) -> dict[str, Any]:
        try:
            return repository.restore_role(role_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.delete("/roles/{role_id}", operation_id="deleteRole", status_code=status.HTTP_204_NO_CONTENT)
    def delete_role(role_id: str) -> None:
        try:
            repository.delete_role(role_id)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Role cần xóa. Tải lại danh sách và thử lại.") from exc
        except InUseError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # -------------------------------------------------------------------------
    # General Settings
    # -------------------------------------------------------------------------
    @router.get("/general", operation_id="getGeneralSettings")
    def get_general_settings() -> dict[str, Any]:
        return repository.get_general_settings()

    @router.put("/general", operation_id="updateGeneralSettings")
    def update_general_settings(payload: GeneralSettingsUpdate) -> dict[str, Any]:
        updates = payload.model_dump(exclude_unset=True)
        return repository.update_general_settings(updates)

    return router
