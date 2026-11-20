"""Integration tests for DATA-002 (backup/restore, integrity) and REL-002 (audit trail, permissions, secret masking)."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tarfile
from uuid import uuid4
import pytest

from agent_cf_server.infrastructure.audit.repository import (
    AuditRepository,
    redact_secrets,
)
from agent_cf_server.infrastructure.persistence.backup import (
    BackupIntegrityError,
    BackupManager,
)
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.robots.repository import RobotRepository
from agent_cf_server.infrastructure.runners.repository import (
    AuthenticationError as RunnerAuthError,
    RunnerRepository,
    SessionInvalidError,
)
from agent_cf_server.infrastructure.runs.repository import (
    AuthenticationError as RunAuthError,
    ConflictError,
    RunRepository,
)
from agent_cf_server.infrastructure.settings.repository import SettingsRepository


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@pytest.fixture
def test_env(tmp_path):
    db_file = tmp_path / "agent_cf_test.sqlite"
    migrations_dir = Path("apps/server/migrations").resolve()
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    database = Database(db_file, migrations_path=migrations_dir)
    database.migrate()

    now = _now_iso()
    # Seed baseline workspace, project, process, version, task
    with database.transaction() as conn:
        conn.execute("INSERT INTO workspaces (id, name) VALUES ('ws-audit', 'Workspace Audit')")
        conn.execute("INSERT INTO workspaces (id, name) VALUES ('ws-other', 'Workspace Other')")
        conn.execute(
            "INSERT INTO projects (id, workspace_id, name, status) VALUES ('proj-1', 'ws-audit', 'Project 1', 'active')"
        )
        conn.execute(
            "INSERT INTO processes (id, project_id, name, status) VALUES ('proc-1', 'proj-1', 'Process 1', 'active')"
        )
        conn.execute(
            "INSERT INTO processes (id, project_id, name, status) VALUES ('proc-pinned', 'proj-1', 'Process Pinned', 'active')"
        )
        # Draft versions first so tasks can be inserted
        conn.execute(
            "INSERT INTO process_versions (id, process_id, version_number, revision, status, definition_format_version, interpreter_version, definition_json) "
            "VALUES ('pv-1', 'proc-1', 1, 1, 'draft', '1', '1', '{}')"
        )
        conn.execute(
            "INSERT INTO process_versions (id, process_id, version_number, revision, status, definition_format_version, interpreter_version, definition_json) "
            "VALUES ('pv-pinned', 'proc-pinned', 1, 1, 'draft', '1', '1', '{}')"
        )
        conn.execute(
            "INSERT INTO tasks (process_version_id, id, task_key, definition_json) "
            "VALUES ('pv-1', 'task-1', 'step-1', json_object('runtime', json_object('adapter', 'antigravity')))"
        )
        # Task pinned to specific runner
        conn.execute(
            "INSERT INTO tasks (process_version_id, id, task_key, definition_json) "
            "VALUES ('pv-pinned', 'task-pinned', 'step-pinned', json_object('runner_id', 'pc-dedicated'))"
        )
        # Publish process versions
        conn.execute(
            "UPDATE process_versions SET status = 'published', snapshot_sha256 = ?, published_at = ? WHERE id = 'pv-1'",
            ('a' * 64, now),
        )
        conn.execute(
            "UPDATE process_versions SET status = 'published', snapshot_sha256 = ?, published_at = ? WHERE id = 'pv-pinned'",
            ('b' * 64, now),
        )

    return {
        "database": database,
        "artifacts_dir": artifacts_dir,
        "tmp_path": tmp_path,
        "run_repo": RunRepository(database),
        "runner_repo": RunnerRepository(database),
        "audit_repo": AuditRepository(database),
    }


# =============================================================================
# DATA-002: Backup and Restore Verification
# =============================================================================

def test_data002_backup_creation_and_online_snapshot_consistency(test_env):
    database = test_env["database"]
    artifacts_dir = test_env["artifacts_dir"]
    run_repo = test_env["run_repo"]
    runner_repo = test_env["runner_repo"]
    tmp_path = test_env["tmp_path"]

    # 1. Create a Runner and active session
    raw_code, _ = runner_repo.create_pairing_code("ws-audit", "PC-1")
    raw_token, runner = runner_repo.exchange_pairing_code(raw_code)
    session = runner_repo.create_session(runner["id"], raw_token)

    # 2. Start a ProcessRun
    created = run_repo.create_from_version(
        version_id="pv-1",
        principal_id="user-op",
        request_key="req-run-1",
        request_sha256="sha-1",
    )
    run_id = created["run_id"]

    # 3. Runner claims task
    work = run_repo.list_work(runner["id"], session["id"])
    assert len(work) >= 1
    task_run_id = work[0]["task_run_id"]
    claimed = run_repo.claim_task_run(
        task_run_id=task_run_id,
        runner_id=runner["id"],
        session_id=session["id"],
        request_key="req-claim-1",
        request_sha256="sha-claim-1",
    )
    attempt_id = claimed["attempt_id"]

    # 4. Register an artifact and write to disk
    art_meta = run_repo.register_artifact(
        attempt_id=attempt_id,
        execution_token=claimed["execution_token"],
        logical_name="summary.md",
        media_type="text/markdown",
        size_bytes=18,
        sha256=hashlib.sha256(b"# Story Summary 42").hexdigest(),
        request_key="req-art-1",
        request_sha256="sha-art-1",
    )
    run_repo.save_artifact_content(
        artifact_id=art_meta["id"],
        execution_token=claimed["execution_token"],
        content=b"# Story Summary 42",
        storage_dir=artifacts_dir,
    )

    # 5. Complete attempt
    run_repo.complete_attempt(
        attempt_id=attempt_id,
        execution_token=claimed["execution_token"],
        outcome="succeeded",
        process_stopped=True,
        exit_code=0,
        output={"result": "OK"},
        error=None,
        artifact_ids=[art_meta["id"]],
        process_evidence=None,
        request_key="req-complete-1",
        request_sha256="sha-complete-1",
    )

    # 6. Execute live backup
    backup_mgr = BackupManager(database, artifacts_dir=artifacts_dir)
    backup_file = tmp_path / "backups" / "agent_cf_backup_1.tar.gz"
    out_path = backup_mgr.create_backup(backup_file)
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    # 7. Verify archive contents
    with tarfile.open(out_path, "r:gz") as tar:
        names = tar.getnames()
        assert "manifest.json" in names
        assert "database.sqlite" in names
        assert f"artifacts/{attempt_id}/summary.md" in names

    # 8. Verify backup without restoring
    verification = backup_mgr.verify_backup(out_path)
    assert verification["valid"] is True
    assert verification["total_artifacts"] == 1
    assert verification["schema_version"] == database.schema_version()


def test_data002_backup_restore_and_consistency_reconciliation(test_env):
    database = test_env["database"]
    artifacts_dir = test_env["artifacts_dir"]
    run_repo = test_env["run_repo"]
    tmp_path = test_env["tmp_path"]

    # Create backup with existing state
    backup_mgr = BackupManager(database, artifacts_dir=artifacts_dir)
    backup_file = tmp_path / "bundle.tar.gz"
    backup_mgr.create_backup(backup_file)

    # Restore to clean location
    restored_db_file = tmp_path / "restored" / "restored.sqlite"
    restored_art_dir = tmp_path / "restored" / "artifacts"

    report = backup_mgr.restore_backup(
        backup_archive=backup_file,
        target_db_path=restored_db_file,
        target_artifacts_dir=restored_art_dir,
    )

    assert report["integrity_check"] == "ok"
    assert report["counts"]["workspaces"] >= 2
    assert report["counts"]["projects"] >= 1
    assert report["counts"]["tasks"] >= 2
    assert report["schema_version"] == database.schema_version()

    # Re-running restore without overwrite must fail
    with pytest.raises(FileExistsError):
        backup_mgr.restore_backup(backup_file, restored_db_file, restored_art_dir, overwrite=False)

    # Re-running restore with overwrite succeeds
    report_ovw = backup_mgr.restore_backup(backup_file, restored_db_file, restored_art_dir, overwrite=True)
    assert report_ovw["integrity_check"] == "ok"


def test_data002_corrupted_backup_detection(test_env):
    database = test_env["database"]
    artifacts_dir = test_env["artifacts_dir"]
    tmp_path = test_env["tmp_path"]

    backup_mgr = BackupManager(database, artifacts_dir=artifacts_dir)
    backup_file = tmp_path / "valid.tar.gz"
    backup_mgr.create_backup(backup_file)

    # Corrupt the archive by modifying manifest
    corrupt_file = tmp_path / "corrupt.tar.gz"
    extract_dir = tmp_path / "tamper"
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(extract_dir)

    # Modify db file so sha256 disagrees with manifest
    db_file = extract_dir / "database.sqlite"
    db_file.write_bytes(db_file.read_bytes() + b"\x00\x00corrupt")

    with tarfile.open(corrupt_file, "w:gz") as tar:
        tar.add(extract_dir / "manifest.json", arcname="manifest.json")
        tar.add(db_file, arcname="database.sqlite")

    with pytest.raises(BackupIntegrityError, match="Database checksum mismatch"):
        backup_mgr.verify_backup(corrupt_file)


# =============================================================================
# REL-002: Audit Trail Tracing & Sensitive Secret Redaction
# =============================================================================

def test_rel002_secret_redaction_utility():
    # 1. Nested dictionary with credential keywords
    payload = {
        "user": "operator_admin",
        "api_key": "sk-1234567890abcdef1234567890",
        "nested": {
            "runner_token": "rt_abcdef12345678901234567890123456",
            "password": "super_secret_password",
            "safe_field": "visible_information",
        },
        "items": [
            {"token": "xyz-token"},
            {"header": "Bearer secret_bearer_token_abc"},
        ],
    }

    redacted = redact_secrets(payload)
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["nested"]["runner_token"] == "***REDACTED***"
    assert redacted["nested"]["password"] == "***REDACTED***"
    assert redacted["nested"]["safe_field"] == "visible_information"
    assert redacted["items"][0]["token"] == "***REDACTED***"
    assert "***REDACTED***" in redacted["items"][1]["header"]
    assert "secret_bearer_token_abc" not in redacted["items"][1]["header"]


def test_rel002_end_to_end_audit_trail_tracing(test_env):
    database = test_env["database"]
    run_repo = test_env["run_repo"]
    runner_repo = test_env["runner_repo"]
    audit_repo = test_env["audit_repo"]

    # 1. Start run
    created = run_repo.create_from_version(
        version_id="pv-1",
        principal_id="operator_alice",
        request_key="req-audit-trace-1",
        request_sha256="sha-at-1",
    )
    run_id = created["run_id"]

    # 2. Pair runner & claim
    raw_code, _ = runner_repo.create_pairing_code("ws-audit", "PC-Audit")
    raw_token, runner = runner_repo.exchange_pairing_code(raw_code)
    session = runner_repo.create_session(runner["id"], raw_token)

    work = run_repo.list_work(runner["id"], session["id"])
    task_run_id = work[0]["task_run_id"]

    claimed = run_repo.claim_task_run(
        task_run_id=task_run_id,
        runner_id=runner["id"],
        session_id=session["id"],
        request_key="req-claim-at-1",
        request_sha256="sha-claim-at-1",
    )
    attempt_id = claimed["attempt_id"]

    # 3. Record attempt observation with sensitive data
    run_repo.record_attempt_observation(
        attempt_id=attempt_id,
        runner_id=runner["id"],
        session_id=session["id"],
        observation_type="process_telemetry",
        data={"metrics": {"cpu": 25.5}, "secret_key": "sensitive_val_999"},
        request_key="req-obs-at-1",
        request_sha256="sha-obs-at-1",
    )

    # 4. Complete attempt
    run_repo.complete_attempt(
        attempt_id=attempt_id,
        execution_token=claimed["execution_token"],
        outcome="succeeded",
        process_stopped=True,
        exit_code=0,
        output={"text": "done"},
        error=None,
        artifact_ids=[],
        process_evidence=None,
        request_key="req-complete-at-1",
        request_sha256="sha-complete-at-1",
    )

    # 5. Query Audit Trail for this Run
    events = audit_repo.get_run_audit_trail(run_id)
    event_types = [e["event_type"] for e in events]

    assert "run_created" in event_types
    assert "task_claimed" in event_types
    assert "attempt_observation" in event_types
    assert "task_completed" in event_types
    assert "run_succeeded" in event_types

    # 6. Verify secret was masked in audit observation
    obs_event = next(e for e in events if e["event_type"] == "attempt_observation")
    assert obs_event["data"]["data"]["secret_key"] == "***REDACTED***"
    assert "sensitive_val_999" not in json.dumps(obs_event)

    # 7. Immutability verification: Triggers prevent UPDATE or DELETE
    with database.transaction() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="audit_immutable"):
            conn.execute("UPDATE audit_events SET actor_id = 'malicious' WHERE run_id = ?", (run_id,))

        with pytest.raises(sqlite3.IntegrityError, match="audit_immutable"):
            conn.execute("DELETE FROM audit_events WHERE run_id = ?", (run_id,))


# =============================================================================
# REL-002: End-to-End Permission & Revocation Enforcement
# =============================================================================

def test_rel002_revoked_runner_and_session_rejection(test_env):
    runner_repo = test_env["runner_repo"]
    run_repo = test_env["run_repo"]

    raw_code, _ = runner_repo.create_pairing_code("ws-audit", "PC-Revoke-Test")
    raw_token, runner = runner_repo.exchange_pairing_code(raw_code)
    session = runner_repo.create_session(runner["id"], raw_token)

    # 1. Authenticate works before revocation
    auth = runner_repo.authenticate_runner(runner["id"], raw_token)
    assert auth["id"] == runner["id"]

    # 2. Revoke runner credential
    runner_repo.revoke_runner(runner["id"])

    # 3. Authenticate now rejected
    with pytest.raises(RunnerAuthError, match="Runner credential has expired or been revoked"):
        runner_repo.authenticate_runner(runner["id"], raw_token)

    # 4. Heartbeat on revoked session rejected
    with pytest.raises(SessionInvalidError, match="is not active \\(revoked\\)"):
        runner_repo.heartbeat(runner["id"], session["id"])

    # 5. Work list on revoked session returns empty
    work = run_repo.list_work(runner["id"], session["id"])
    assert work == []


def test_rel002_cross_workspace_unauthorized_claim_rejection(test_env):
    runner_repo = test_env["runner_repo"]
    run_repo = test_env["run_repo"]

    # Runner in ws-other
    raw_code, _ = runner_repo.create_pairing_code("ws-other", "PC-Other-WS")
    raw_token, runner = runner_repo.exchange_pairing_code(raw_code)
    session = runner_repo.create_session(runner["id"], raw_token)

    # TaskRun is in ws-audit
    created = run_repo.create_from_version(
        version_id="pv-1",
        principal_id="user-1",
        request_key="req-cross-ws",
        request_sha256="sha-cross-ws",
    )
    with test_env["database"].connect() as conn:
        tr = conn.execute("SELECT id FROM task_runs WHERE run_id = ?", (created["run_id"],)).fetchone()
        task_run_id = tr["id"]

    # Attempt cross-workspace claim -> must reject with RunAuthError
    with pytest.raises(RunAuthError, match="Runner workspace mismatch"):
        run_repo.claim_task_run(
            task_run_id=task_run_id,
            runner_id=runner["id"],
            session_id=session["id"],
            request_key="req-claim-cross",
            request_sha256="sha-claim-cross",
        )


def test_rel002_pinned_runner_mismatch_rejection(test_env):
    runner_repo = test_env["runner_repo"]
    run_repo = test_env["run_repo"]

    # Task task-pinned is pinned to runner 'pc-dedicated'
    # Register a different runner 'pc-normal'
    raw_code, _ = runner_repo.create_pairing_code("ws-audit", "PC-Normal")
    raw_token, runner = runner_repo.exchange_pairing_code(raw_code)
    session = runner_repo.create_session(runner["id"], raw_token)

    created = run_repo.create_from_version(
        version_id="pv-pinned",
        principal_id="user-1",
        request_key="req-pinned",
        request_sha256="sha-pinned",
    )
    with test_env["database"].connect() as conn:
        tr = conn.execute("SELECT id FROM task_runs WHERE run_id=? AND task_id='task-pinned'", (created["run_id"],)).fetchone()
        task_run_id = tr["id"]

    with pytest.raises(ConflictError, match="Task is pinned to runner 'pc-dedicated'"):
        run_repo.claim_task_run(
            task_run_id=task_run_id,
            runner_id=runner["id"],
            session_id=session["id"],
            request_key="req-claim-pinned",
            request_sha256="sha-claim-pinned",
        )


def test_rel002_stale_lease_and_invalid_token_rejection(test_env):
    database = test_env["database"]
    runner_repo = test_env["runner_repo"]
    run_repo = test_env["run_repo"]

    raw_code, _ = runner_repo.create_pairing_code("ws-audit", "PC-Lease-Test")
    raw_token, runner = runner_repo.exchange_pairing_code(raw_code)
    session = runner_repo.create_session(runner["id"], raw_token)

    created = run_repo.create_from_version(
        version_id="pv-1",
        principal_id="user-1",
        request_key="req-lease",
        request_sha256="sha-lease",
    )
    with database.connect() as conn:
        tr = conn.execute("SELECT id FROM task_runs WHERE run_id = ?", (created["run_id"],)).fetchone()
        task_run_id = tr["id"]

    claimed = run_repo.claim_task_run(
        task_run_id=task_run_id,
        runner_id=runner["id"],
        session_id=session["id"],
        request_key="req-claim-lease",
        request_sha256="sha-claim-lease",
    )
    attempt_id = claimed["attempt_id"]

    # 1. Invalid execution token rejected
    with pytest.raises(RunAuthError, match="Invalid execution token"):
        run_repo.complete_attempt(
            attempt_id=attempt_id,
            execution_token="wrong_token_hex_999",
            outcome="succeeded",
            process_stopped=True,
            exit_code=0,
            output={},
            error=None,
            artifact_ids=[],
            process_evidence=None,
            request_key="req-comp-wrong",
            request_sha256="sha-comp-wrong",
        )

    # 2. Expired lease rejected
    expired_at = (datetime.now(timezone.utc) - timedelta(seconds=100)).isoformat().replace("+00:00", "Z")
    with database.transaction() as conn:
        conn.execute("UPDATE execution_grants SET expires_at = ? WHERE attempt_id = ?", (expired_at, attempt_id))

    with pytest.raises(ConflictError, match="stale_execution: lease has expired"):
        run_repo.complete_attempt(
            attempt_id=attempt_id,
            execution_token=claimed["execution_token"],
            outcome="succeeded",
            process_stopped=True,
            exit_code=0,
            output={},
            error=None,
            artifact_ids=[],
            process_evidence=None,
            request_key="req-comp-expired",
            request_sha256="sha-comp-expired",
        )
