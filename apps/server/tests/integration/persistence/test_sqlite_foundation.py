from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sqlite3

import pytest

from agent_cf_server.infrastructure.persistence.database import Database, MigrationError
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.runs.repository import (
    IdempotencyConflict,
    RevisionConflict,
    RunRepository,
)


@pytest.fixture
def definition():
    return {
        "definition_format_version": "1",
        "interpreter_version": "dag-v1",
        "tasks": [
            {"id": "first", "task_key": "first", "runtime": {"model_id": "fixture-model"}},
            {"id": "last", "task_key": "last", "runtime": {"model_id": "fixture-model"}},
        ],
        "dependencies": [{"source_task_id": "first", "target_task_id": "last"}],
    }


@pytest.fixture
def database(tmp_path):
    database = Database(tmp_path / "business.sqlite3")
    assert database.migrate() == 24
    return database


def publish(database, definition, version_id="version-1", version_number=1):
    projects = ProjectRepository(database)
    projects.create_workspace(workspace_id="workspace", name="Workspace")
    projects.create_project(project_id="project", workspace_id="workspace", name="Project")
    ProcessRepository(database).create_process(process_id="process", project_id="project", name="Process")
    ProcessRepository(database).store_published(
        workspace_id="workspace", project_id="project", process_id="process",
        version_id=version_id, version_number=version_number,
        definition=definition, snapshot_sha256="a" * 64,
    )


def create_run(database, key="create-1"):
    return RunRepository(database).create_from_version(
        version_id="version-1", run_input={"text": "sample"}, principal_id="operator",
        request_key=key, request_sha256="b" * 64,
    )["run_id"]


def test_fresh_and_repeated_migrations(database):
    assert database.migrate() == 24
    assert database.health() == {"schema_version": 24, "foreign_keys": 1, "journal_mode": "wal"}
    with database.connect() as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert len(connection.execute("SELECT * FROM schema_migrations").fetchall()) == 24


def test_skill_scope_migration_preserves_existing_skills_as_global(tmp_path):
    db = Database(tmp_path / "scope-upgrade.sqlite3")
    db.migrate(target_version=11)
    with db.transaction() as conn:
        conn.execute("INSERT INTO skills(id,name,description) VALUES ('existing','Existing Skill','Preserved')")
        conn.execute("INSERT INTO skill_versions(id,skill_id,version_number,status,instructions) VALUES ('v','existing',1,'draft','Original instructions')")
    assert db.migrate() == 24
    with db.connect() as conn:
        assert dict(conn.execute("SELECT name,description,is_global FROM skills WHERE id='existing'").fetchone()) == {"name": "Existing Skill", "description": "Preserved", "is_global": 1}
        assert conn.execute("SELECT instructions FROM skill_versions WHERE id='v'").fetchone()[0] == "Original instructions"
        assert conn.execute("SELECT COUNT(*) FROM skill_projects").fetchone()[0] == 0


def test_upgrade_preserves_existing_definition(tmp_path, definition):
    database = Database(tmp_path / "upgrade.db")
    assert database.migrate(target_version=1) == 1
    publish(database, definition)
    assert Database(database.path).migrate() == 24
    assert ProcessRepository(Database(database.path)).get_version("version-1")["definition"] == definition
    assert RunRepository(Database(database.path)).get(create_run(database))["input"] == {"text": "sample"}


def test_failed_migration_rolls_back_schema_and_history(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_broken.sql").write_text(
        "CREATE TABLE should_rollback(id TEXT);\nINSERT INTO missing_table VALUES (1);\n", encoding="utf-8"
    )
    database = Database(tmp_path / "broken.db", migrations_path=migrations)
    with pytest.raises(sqlite3.OperationalError):
        database.migrate()
    with database.connect() as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='should_rollback'").fetchone() is None
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0


def test_applied_migration_checksum_and_downgrade_rejected(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    migration = migrations / "001_test.sql"
    migration.write_text("CREATE TABLE original(id TEXT);\n", encoding="utf-8")
    database = Database(tmp_path / "checksum.db", migrations_path=migrations)
    database.migrate()
    with pytest.raises(MigrationError, match="Downgrade"):
        database.migrate(target_version=0)
    migration.write_text("CREATE TABLE changed(id TEXT);\n", encoding="utf-8")
    with pytest.raises(MigrationError, match="modified"):
        database.migrate()


def test_published_definition_survives_mutable_caller_and_reconnect(database, definition):
    original = deepcopy(definition)
    publish(database, definition)
    definition["tasks"][0]["runtime"]["model_id"] = "changed"
    assert ProcessRepository(Database(database.path)).get_version("version-1")["definition"] == original
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("UPDATE tasks SET definition_json='{}' WHERE id='first'")
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("UPDATE process_versions SET definition_json='{}' WHERE id='version-1'")


def test_publish_failure_rolls_back_entire_definition(database, definition):
    definition["dependencies"][0]["target_task_id"] = "missing"
    with pytest.raises(sqlite3.IntegrityError):
        publish(database, definition)
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM process_versions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1


def test_run_taskruns_audit_outbox_and_receipt_commit_together(database, definition):
    publish(database, definition)
    run_id = create_run(database)
    saved = RunRepository(Database(database.path)).get(run_id)
    assert saved["status"] == "queued"
    assert saved["snapshot_sha256"] == "a" * 64
    assert [task["task_id"] for task in saved["task_runs"]] == ["first", "last"]
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_events WHERE run_id=?", (run_id,)).fetchone()[0] == 1
        assert connection.execute("SELECT command_type FROM engine_outbox WHERE run_id=?", (run_id,)).fetchone()[0] == "start_run"
        assert connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1


def test_run_creation_rolls_back_when_outbox_fails(database, definition):
    publish(database, definition)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER fail_outbox BEFORE INSERT ON engine_outbox BEGIN SELECT RAISE(ABORT,'test fault'); END")
    with pytest.raises(sqlite3.IntegrityError, match="test fault"):
        create_run(database)
    with database.connect() as connection:
        for table in ("process_runs", "task_runs", "run_events", "audit_events", "receipts"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_concurrent_create_deduplicates_in_database(database, definition):
    publish(database, definition)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create_run(Database(database.path)), range(2)))
    assert results[0] == results[1]
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM process_runs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0] == 2
    with pytest.raises(IdempotencyConflict):
        RunRepository(database).create_from_version(
            version_id="version-1", run_input={"text": "changed"}, principal_id="operator",
            request_key="create-1", request_sha256="c" * 64,
        )


def test_reconciling_compare_and_set_inbox_and_sequence(database, definition):
    publish(database, definition)
    run_id = create_run(database)
    with database.transaction() as connection:
        connection.execute("UPDATE process_runs SET status='running' WHERE id=?", (run_id,))
    repository = RunRepository(database)
    command = dict(run_id=run_id, expected_revision=1, command_id="lost-connection", request_sha256="d" * 64, reason="lease_expired")
    assert repository.mark_reconciling(**command) == {"run_id": run_id, "revision": 2}
    assert repository.mark_reconciling(**command) == {"run_id": run_id, "revision": 2}
    assert repository.get(run_id)["status"] == "reconciling"
    with pytest.raises(RevisionConflict):
        repository.mark_reconciling(**{**command, "command_id": "stale-command"})
    with pytest.raises(IdempotencyConflict):
        repository.mark_reconciling(**{**command, "request_sha256": "e" * 64})
    with database.connect() as connection:
        assert [row[0] for row in connection.execute("SELECT sequence FROM run_events WHERE run_id=? ORDER BY sequence", (run_id,))] == [1, 2]
        assert connection.execute("SELECT COUNT(*) FROM engine_inbox").fetchone()[0] == 1


def seed_attempt(database, run_id):
    with database.transaction() as connection:
        task = connection.execute("SELECT id FROM task_runs WHERE run_id=? ORDER BY task_id", (run_id,)).fetchone()[0]
        connection.execute("INSERT INTO runners(id,workspace_id,status) VALUES ('runner','workspace','online')")
        connection.execute("INSERT INTO runner_sessions(id,runner_id,status,created_at) VALUES ('session','runner','active','2026-11-16T00:00:00Z')")
        connection.execute(
            "INSERT INTO attempts(id,task_run_id,run_id,runner_id,session_id,generation,status,claimed_at,execution_deadline_at) "
            "VALUES ('attempt',?,?,'runner','session',1,'reconciling','2026-11-16T00:00:00Z','2026-11-16T00:30:00Z')",
            (task, run_id),
        )
        connection.execute(
            "INSERT INTO execution_grants(attempt_id,task_run_id,runner_id,session_id,generation,token_hash,expires_at) "
            "VALUES ('attempt',?,'runner','session',1,'hash-only','2026-11-16T00:01:00Z')", (task,)
        )
        return task


def test_reconciling_attempt_cannot_be_reissued_and_artifact_survives(database, definition):
    publish(database, definition)
    run_id = create_run(database)
    task = seed_attempt(database, run_id)
    with database.transaction() as connection:
        connection.execute("INSERT INTO artifacts VALUES ('artifact','attempt','story','text/plain',5,?,'available','objects/artifact','2026-11-16T00:00:00Z')", ("f" * 64,))
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO attempts(id,task_run_id,run_id,runner_id,session_id,generation,status,claimed_at,execution_deadline_at) "
            "VALUES ('attempt-2',?,?,'runner','session',2,'claimed','2026-11-16T00:02:00Z','2026-11-16T00:32:00Z')",
            (task, run_id),
        )
    with Database(database.path).connect() as connection:
        assert connection.execute("SELECT status FROM attempts").fetchone()[0] == "reconciling"
        assert connection.execute("SELECT token_hash FROM execution_grants").fetchone()[0] == "hash-only"
        assert connection.execute("SELECT storage_key FROM artifacts").fetchone()[0] == "objects/artifact"
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("UPDATE artifacts SET sha256=? WHERE id='artifact'", ("0" * 64,))


def test_foreign_keys_and_terminal_history_protected(database, definition):
    publish(database, definition)
    run_id = create_run(database)
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO task_runs(id,run_id,process_version_id,task_id,status) VALUES ('bad',?,'version-1','missing','pending')", (run_id,))
    with database.transaction() as connection:
        connection.execute("UPDATE task_runs SET status='skipped' WHERE run_id=?", (run_id,))
        connection.execute("UPDATE process_runs SET status='failed',ended_at='2026-11-16T00:00:00Z' WHERE id=?", (run_id,))
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="terminal"):
        connection.execute("UPDATE process_runs SET status='running',ended_at=NULL WHERE id=?", (run_id,))
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("DELETE FROM run_events WHERE run_id=?", (run_id,))


def test_lock_timeout_is_not_silent(tmp_path):
    first = Database(tmp_path / "lock.db")
    first.migrate()
    second = Database(first.path, busy_timeout_ms=10)
    with first.transaction():
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            with second.transaction():
                pass


def test_health_never_creates_a_missing_database(tmp_path):
    database = Database(tmp_path / "absent" / "business.sqlite3")
    with pytest.raises(sqlite3.OperationalError):
        database.health()
    assert not database.path.exists()
    assert not database.path.parent.exists()


def test_health_rejects_empty_replacement_without_modifying_it(tmp_path):
    database = Database(tmp_path / "replaced.sqlite3")
    database.migrate()
    database.path.unlink()
    with sqlite3.connect(database.path):
        pass
    with pytest.raises(MigrationError, match="not current"):
        database.health()
    assert database.path.stat().st_size == 0


def test_health_rejects_old_schema_without_upgrading(tmp_path):
    database = Database(tmp_path / "old.sqlite3")
    database.migrate(target_version=1)
    with pytest.raises(MigrationError, match="not current"):
        database.health()
    assert database.schema_version() == 1


def test_health_rejects_missing_table_and_invalid_history(database):
    with database.transaction() as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version=24")
    with pytest.raises(MigrationError, match="history is incomplete"):
        database.health()
    # No repair is attempted by a health call.
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 23
    with database.transaction() as connection:
        connection.execute("DROP TABLE artifacts")
    with pytest.raises(MigrationError, match="missing required tables"):
        database.health()


def test_http_health_returns_503_after_database_loss(tmp_path):
    from fastapi.testclient import TestClient
    from agent_cf_server.bootstrap.config import ServerSettings
    from agent_cf_server.bootstrap.server import create_app

    path = tmp_path / "lost.sqlite3"
    app = create_app(ServerSettings(database_path=path, temporal_enabled=False))
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        path.unlink()
        response = client.get("/healthz")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable", "component": "database"}
        assert client.get("/readyz").status_code == 503
        assert not path.exists()


def test_store_published_never_creates_missing_organizational_parents(database, definition):
    values = dict(workspace_id="workspace", project_id="project", process_id="process",
                  version_id="version", version_number=1, definition=definition, snapshot_sha256="a" * 64)
    with pytest.raises(ValueError, match="existing Process"):
        ProcessRepository(database).store_published(**values)
    with database.connect() as connection:
        for table in ("workspaces", "projects", "processes", "process_versions", "tasks", "dependencies"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    projects = ProjectRepository(database)
    projects.create_workspace(workspace_id="workspace", name="Workspace")
    projects.create_project(project_id="project", workspace_id="workspace", name="Project")
    with pytest.raises(ValueError, match="existing Process"):
        ProcessRepository(database).store_published(**values)
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM processes").fetchone()[0] == 0


@pytest.mark.parametrize("wrong_parent", ["workspace_id", "project_id"])
def test_store_published_rejects_mismatched_ownership(database, definition, wrong_parent):
    projects = ProjectRepository(database)
    projects.create_workspace(workspace_id="workspace", name="Workspace")
    projects.create_project(project_id="project", workspace_id="workspace", name="Project")
    repository = ProcessRepository(database)
    repository.create_process(process_id="process", project_id="project", name="Process")
    values = dict(workspace_id="workspace", project_id="project", process_id="process",
                  version_id="version", version_number=1, definition=definition, snapshot_sha256="a" * 64)
    values[wrong_parent] = "wrong-parent"
    with pytest.raises(ValueError, match="ownership"):
        repository.store_published(**values)
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM process_versions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM processes").fetchone()[0] == 1


def test_event_cannot_mix_attempt_with_another_task(database, definition):
    publish(database, definition)
    run_id = create_run(database)
    first_task = seed_attempt(database, run_id)
    with database.connect() as connection:
        other_task = connection.execute("SELECT id FROM task_runs WHERE run_id=? AND id<>?", (run_id, first_task)).fetchone()[0]
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="event_attempt_task_mismatch"):
        connection.execute(
            "INSERT INTO run_events(id,run_id,sequence,event_type,task_run_id,attempt_id,data_json,recorded_at) "
            "VALUES ('bad-event',?,2,'started',?,'attempt','{}','2026-11-16T00:00:00Z')", (run_id, other_task)
        )


def test_terminal_run_rejects_pending_tasks_or_unknown_attempt(database, definition):
    publish(database, definition)
    run_id = create_run(database)
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="unsettled"):
        connection.execute("UPDATE process_runs SET status='succeeded',ended_at='2026-11-16T00:00:00Z' WHERE id=?", (run_id,))
    seed_attempt(database, run_id)
    with database.transaction() as connection:
        connection.execute("UPDATE task_runs SET status='skipped' WHERE run_id=?", (run_id,))
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="unsettled"):
        connection.execute("UPDATE process_runs SET status='failed',ended_at='2026-11-16T00:00:00Z' WHERE id=?", (run_id,))


def test_history_cannot_be_deleted_and_task_queue_policy_survives(database, definition):
    publish(database, definition)
    run_id = create_run(database)
    seed_attempt(database, run_id)
    with database.transaction() as connection:
        connection.execute("UPDATE task_runs SET queued_at='2026-11-16T00:00:00Z',queue_deadline_at='2026-11-17T00:00:00Z' WHERE run_id=?", (run_id,))
        connection.execute("INSERT INTO artifacts VALUES ('artifact','attempt','story','text/plain',5,?,'available','objects/artifact','2026-11-16T00:00:00Z')", ("f" * 64,))
    for sql in ("DELETE FROM task_runs", "DELETE FROM attempts", "DELETE FROM process_runs", "DELETE FROM artifacts", "DELETE FROM receipts"):
        with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(sql)
    with Database(database.path).connect() as connection:
        assert connection.execute("SELECT queue_deadline_at FROM task_runs LIMIT 1").fetchone()[0] == '2026-11-17T00:00:00Z'
