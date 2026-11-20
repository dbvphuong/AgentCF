"""Minimal Project/Workspace storage for foundation persistence.

These operations are called explicitly by a trusted bootstrap/use case; storing a
ProcessVersion never creates organizational parents as an implicit side effect.
"""

from agent_cf_server.infrastructure.persistence.database import Database


class ProjectRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_workspace(self, *, workspace_id: str, name: str) -> None:
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO workspaces(id,name) VALUES (?,?)", (workspace_id, name))

    def create_project(self, *, project_id: str, workspace_id: str, name: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO projects(id,workspace_id,name) VALUES (?,?,?)",
                (project_id, workspace_id, name),
            )
