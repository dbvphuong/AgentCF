"""HTTP boundary for Projects, Team, Targets, and the Process editor."""

from datetime import date
import sqlite3
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent_cf_server.infrastructure.projects.management import CloneConflictError, ConfigurationConflictError, ProjectManagement


class Named(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=128)
    description: str = ""


class ProjectInput(Named):
    workspace_id: str = Field(min_length=1)
    pm_agent_id: str = Field(min_length=1)
    working_directory: str | None = None


class TeamInput(BaseModel):
    agent_ids: list[str]


class CloneProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=128)


class TargetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=128)
    period: Literal["weekly", "monthly"]
    target_count: int = Field(gt=0)
    completed_count: int = Field(default=0, ge=0)
    starts_on: date
    ends_on: date
    acceptance_criteria: str = Field(min_length=1)


class DraftInput(BaseModel):
    definition: dict[str, Any]
    revision: int = Field(ge=1)


class RevisionInput(BaseModel):
    revision: int = Field(ge=1)


class ConfigurationInput(BaseModel):
    definition: dict[str, Any]
    expected_token: str = Field(min_length=1)


def projects_router(service: ProjectManagement) -> APIRouter:
    router = APIRouter(tags=["projects"])

    def call(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KeyError as exc:
            raise HTTPException(404, "Không tìm thấy tài nguyên được tham chiếu") from exc
        except (CloneConflictError, ConfigurationConflictError) as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, "Dữ liệu xung đột hoặc đang được tham chiếu") from exc

    @router.get("/v1/workspaces", operation_id="listWorkspaces")
    def workspaces():
        return service.workspaces()

    @router.get("/v1/processes/{process_id}/configuration", operation_id="getProcessConfiguration")
    def configuration(process_id: str):
        return call(service.get_configuration, process_id)

    @router.put("/v1/processes/{process_id}/configuration", operation_id="saveProcessConfiguration")
    def save_configuration(process_id: str, payload: ConfigurationInput):
        return call(service.save_configuration, process_id, payload.definition, payload.expected_token)

    @router.get("/v1/processes/{process_id}/run-context", operation_id="getCurrentRunContext")
    def current_context(process_id: str):
        return call(service.configuration_context, process_id)

    @router.post("/v1/workspaces", operation_id="createWorkspace", status_code=201)
    def create_workspace(payload: Named):
        from uuid import uuid4
        wid = str(uuid4())
        with service.database.transaction() as conn:
            conn.execute("INSERT INTO workspaces VALUES (?,?)", (wid, payload.name))
        return {"id": wid, "name": payload.name}

    @router.get("/v1/projects", operation_id="listProjects")
    def projects():
        return service.list_projects()

    @router.post("/v1/projects", operation_id="createProject", status_code=201)
    def create_project(payload: ProjectInput):
        return call(service.save_project, payload.model_dump())

    @router.get("/v1/projects/{project_id}", operation_id="getProject",
                description="Project detail with read-only Team: PM union Agent IDs from nodes in each Process's latest saved version, deduplicated. Legacy manual memberships are ignored.")
    def get_project(project_id: str):
        return call(service.get_project, project_id)

    @router.post("/v1/projects/{project_id}/clone", operation_id="cloneProject", status_code=201)
    def clone_project(
        project_id: str, payload: CloneProjectInput,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=1, max_length=128),
    ):
        return call(service.clone_project, project_id, payload.name, idempotency_key)

    @router.patch("/v1/projects/{project_id}", operation_id="updateProject")
    def update_project(project_id: str, payload: ProjectInput):
        return call(service.save_project, payload.model_dump(), project_id)

    @router.put("/v1/projects/{project_id}/team", operation_id="updateProjectTeam", deprecated=True,
                description="Team is read-only and derived from Project PM and nodes in the latest saved version of each Process. Legacy writes return 422 without changing membership.")
    def team(project_id: str, payload: TeamInput):
        return call(service.save_team, project_id, payload.agent_ids)

    @router.post("/v1/projects/{project_id}/targets", operation_id="createProjectTarget", status_code=201)
    def create_target(project_id: str, payload: TargetInput):
        return call(service.save_target, project_id, payload.model_dump(mode="json"))

    @router.patch("/v1/projects/{project_id}/targets/{target_id}", operation_id="updateProjectTarget")
    def update_target(project_id: str, target_id: str, payload: TargetInput):
        return call(service.save_target, project_id, payload.model_dump(mode="json"), target_id)

    @router.post("/v1/projects/{project_id}/processes", operation_id="createProcess", status_code=201)
    def create_process(project_id: str, payload: Named):
        return call(service.save_process, project_id, payload.model_dump())

    @router.get("/v1/processes/{process_id}", operation_id="getProcess")
    def get_process(process_id: str):
        return call(service.get_process, process_id)

    @router.get("/v1/processes/{process_id}/versions/{version_id}", operation_id="getProcessVersion")
    def get_version(process_id: str, version_id: str):
        process = call(service.get_process, process_id)
        for version in process["versions"]:
            if version["id"] == version_id:
                return version
        raise HTTPException(404, "Version not found in Process")

    @router.patch("/v1/processes/{process_id}", operation_id="updateProcess")
    def update_process(process_id: str, payload: Named):
        process = call(service.get_process, process_id)
        return call(service.save_process, process["project_id"], payload.model_dump(), process_id)

    @router.post("/v1/processes/{process_id}/draft", operation_id="createProcessDraft")
    def draft(process_id: str):
        return call(service.draft, process_id)

    @router.put("/v1/processes/{process_id}/versions/{version_id}", operation_id="saveProcessDraft")
    def save(process_id: str, version_id: str, payload: DraftInput):
        return call(service.save_draft, process_id, version_id, payload.definition, payload.revision)

    @router.post("/v1/processes/{process_id}/versions/{version_id}/validate", operation_id="validateProcessDraft")
    def validate(process_id: str, version_id: str, payload: RevisionInput):
        return call(service.publish, process_id, version_id, payload.revision, validate_only=True)

    @router.post("/v1/processes/{process_id}/versions/{version_id}/publish", operation_id="publishProcessDraft")
    def publish(process_id: str, version_id: str, payload: RevisionInput):
        return call(service.publish, process_id, version_id, payload.revision)

    @router.post("/v1/projects/{project_id}/archive", operation_id="archiveProject")
    def archive_project(project_id: str):
        return call(service.lifecycle, "project", project_id, True)

    @router.post("/v1/projects/{project_id}/restore", operation_id="restoreProject")
    def restore_project(project_id: str):
        return call(service.lifecycle, "project", project_id, False)

    @router.post("/v1/processes/{process_id}/archive", operation_id="archiveProcess")
    def archive_process(process_id: str):
        return call(service.lifecycle, "process", process_id, True)

    @router.post("/v1/processes/{process_id}/restore", operation_id="restoreProcess")
    def restore_process(process_id: str):
        return call(service.lifecycle, "process", process_id, False)

    @router.delete("/v1/projects/{project_id}", operation_id="deleteProject", description="Permanently delete Project and its owned definitions/history; reject unfinished Runs. Shared catalog and PC files are preserved.")
    def delete_project(project_id: str):
        return call(service.delete, "project", project_id)

    @router.delete("/v1/processes/{process_id}", operation_id="deleteProcess", description="Permanently delete Process and its owned versions/history; reject unfinished Runs. Shared catalog and PC files are preserved.")
    def delete_process(process_id: str):
        return call(service.delete, "process", process_id)

    return router
