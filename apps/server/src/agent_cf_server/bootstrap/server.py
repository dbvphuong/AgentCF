"""Run the local HTTP scaffold or explicitly apply business DB migrations."""

import argparse
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent_cf_server.api.agents import agents_router
from agent_cf_server.api.health import health_router
from agent_cf_server.api.overview import overview_router
from agent_cf_server.api.projects import projects_router
from agent_cf_server.api.reviews import reviews_router
from agent_cf_server.api.robots import robots_router
from agent_cf_server.api.runners import runners_router
from agent_cf_server.api.runs import runs_router
from agent_cf_server.api.schedules import schedules_router
from agent_cf_server.api.settings import settings_router
from agent_cf_server.api.skills import skills_router
from agent_cf_server.bootstrap.config import ServerSettings, load_settings
from agent_cf_server.infrastructure.agents.repository import AgentRepository
from agent_cf_server.infrastructure.agents.review_repository import ReviewRepository
from agent_cf_server.infrastructure.overview.repository import OverviewRepository
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.projects.management import ProjectManagement
from agent_cf_server.infrastructure.processes.schedule_repository import ScheduleRepository
from agent_cf_server.infrastructure.robots.repository import RobotRepository
from agent_cf_server.infrastructure.runners.repository import RunnerRepository
from agent_cf_server.infrastructure.runs.repository import RunRepository
from agent_cf_server.infrastructure.settings.repository import SettingsRepository
from agent_cf_server.api.client_download import client_download_router
from agent_cf_server.infrastructure.settings.ai_tool_models import AiToolModelRepository
from agent_cf_server.api.ai_tool_models import ai_tool_models_router
from agent_cf_server.infrastructure.skills.repository import SkillRepository


def create_app(settings: ServerSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    database = Database(settings.database_path, busy_timeout_ms=settings.database_busy_timeout_ms)
    settings_repo = SettingsRepository(database)
    skills_repo = SkillRepository(database)
    agents_repo = AgentRepository(database)
    reviews_repo = ReviewRepository(database)
    robots_repo = RobotRepository(database)
    runners_repo = RunnerRepository(database)
    runs_repo = RunRepository(database)
    schedules_repo = ScheduleRepository(database)
    overview_repo = OverviewRepository(database)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.migrate()
        from agent_cf_server.infrastructure.runs.artifact_cleanup import cleanup_artifacts
        cleanup_artifacts(database, settings.artifacts_dir)
        yield

    app = FastAPI(title="Agent CF foundation", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router(database, settings))
    app.include_router(client_download_router(settings.client_installer_path.resolve()))
    app.include_router(projects_router(ProjectManagement(database, settings.artifacts_dir)))
    app.include_router(overview_router(overview_repo))
    app.include_router(settings_router(settings_repo))
    app.include_router(ai_tool_models_router(AiToolModelRepository(database)))
    app.include_router(skills_router(skills_repo))
    app.include_router(agents_router(agents_repo))
    app.include_router(reviews_router(reviews_repo))
    app.include_router(robots_router(robots_repo))
    app.include_router(runners_router(runners_repo))
    app.include_router(schedules_router(schedules_repo, runs_repo))
    app.include_router(runs_router(runs_repo, settings.artifacts_dir))
    app.state.database = database
    app.state.settings_repo = settings_repo
    app.state.skills_repo = skills_repo
    app.state.agents_repo = agents_repo
    app.state.reviews_repo = reviews_repo
    app.state.robots_repo = robots_repo
    app.state.runners_repo = runners_repo
    app.state.runs_repo = runs_repo
    app.state.schedules_repo = schedules_repo
    app.state.overview_repo = overview_repo
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("serve", "migrate"), default="serve")
    args = parser.parse_args()
    settings = load_settings()
    if args.command == "migrate":
        database = Database(settings.database_path, busy_timeout_ms=settings.database_busy_timeout_ms)
        print(f"Business schema version: {database.migrate()}")
        return
    import uvicorn

    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
