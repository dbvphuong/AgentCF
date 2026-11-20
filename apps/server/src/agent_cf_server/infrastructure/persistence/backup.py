"""Consistent backup, restore, and integrity reconciliation for SQLite & artifacts (DATA-002)."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile
from typing import Any

from agent_cf_server.infrastructure.persistence.database import Database


class BackupError(RuntimeError):
    """Backup creation, verification, or restoration failure."""


class BackupIntegrityError(BackupError):
    """Checksum mismatch, missing artifact, or schema corruption during backup/restore."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class BackupManager:
    def __init__(self, database: Database, artifacts_dir: Path | str | None = None) -> None:
        self.database = database
        self.artifacts_dir = Path(artifacts_dir).resolve() if artifacts_dir else (database.path.parent / "artifacts")

    def create_backup(self, output_path: Path | str) -> Path:
        """Create a consistent point-in-time backup bundle containing SQLite snapshot and artifacts."""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        with tempfile.TemporaryDirectory(prefix="agentcf_backup_") as tmp_dir:
            staging = Path(tmp_dir)
            db_backup_path = staging / "database.sqlite"
            artifacts_backup_dir = staging / "artifacts"
            artifacts_backup_dir.mkdir(parents=True, exist_ok=True)

            # 1. Consistent SQLite Online Backup (safe even during active transactions in WAL mode)
            with self.database.connect(read_only=True) as src_conn:
                dest_conn = sqlite3.connect(db_backup_path)
                try:
                    src_conn.backup(dest_conn)
                finally:
                    dest_conn.close()

            # Verify integrity of SQLite backup copy
            verify_conn = sqlite3.connect(db_backup_path)
            try:
                check = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
                if check != "ok":
                    raise BackupIntegrityError(f"Database backup integrity check failed: {check}")
                schema_version = verify_conn.execute("PRAGMA user_version").fetchone()[0]

                # 2. Collect artifacts listed in database
                verify_conn.row_factory = sqlite3.Row
                artifact_rows = verify_conn.execute(
                    "SELECT id, logical_name, media_type, size_bytes, sha256, storage_key "
                    "FROM artifacts WHERE availability = 'available'"
                ).fetchall()
            finally:
                verify_conn.close()

            db_sha256 = _sha256_file(db_backup_path)
            db_size = db_backup_path.stat().st_size

            manifest_artifacts: dict[str, dict[str, Any]] = {}
            for row in artifact_rows:
                art_id = row["id"]
                storage_key = row["storage_key"]
                art_source = self.artifacts_dir / storage_key

                if not art_source.exists():
                    raise BackupIntegrityError(
                        f"Artifact '{art_id}' (file '{storage_key}') registered in DB but missing from disk"
                    )

                actual_sha = _sha256_file(art_source)
                if actual_sha != row["sha256"]:
                    raise BackupIntegrityError(
                        f"Artifact '{art_id}' sha256 mismatch: expected {row['sha256']}, got {actual_sha}"
                    )

                art_dest = artifacts_backup_dir / storage_key
                art_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(art_source, art_dest)

                manifest_artifacts[art_id] = {
                    "logical_name": row["logical_name"],
                    "media_type": row["media_type"],
                    "size_bytes": row["size_bytes"],
                    "sha256": row["sha256"],
                    "storage_key": storage_key,
                }

            # 3. Write manifest.json
            manifest = {
                "manifest_version": "1.0",
                "created_at": now,
                "schema_version": schema_version,
                "db_filename": "database.sqlite",
                "db_sha256": db_sha256,
                "db_size_bytes": db_size,
                "artifacts": manifest_artifacts,
                "total_artifacts": len(manifest_artifacts),
            }
            manifest_path = staging / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

            # 4. Package staging into compressed tar archive (.tar.gz)
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(manifest_path, arcname="manifest.json")
                tar.add(db_backup_path, arcname="database.sqlite")
                if manifest_artifacts:
                    tar.add(artifacts_backup_dir, arcname="artifacts")

        return output_path

    def verify_backup(self, backup_archive: Path | str) -> dict[str, Any]:
        """Verify the integrity of a backup archive without touching the live database."""
        backup_archive = Path(backup_archive).resolve()
        if not backup_archive.exists():
            raise FileNotFoundError(f"Backup archive not found: {backup_archive}")

        with tempfile.TemporaryDirectory(prefix="agentcf_verify_") as tmp_dir:
            staging = Path(tmp_dir)
            with tarfile.open(backup_archive, "r:gz") as tar:
                tar.extractall(staging)

            manifest_file = staging / "manifest.json"
            if not manifest_file.exists():
                raise BackupIntegrityError("Backup archive missing manifest.json")

            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            if manifest.get("manifest_version") != "1.0":
                raise BackupIntegrityError(f"Unsupported manifest version: {manifest.get('manifest_version')}")

            # Verify SQLite DB
            db_file = staging / manifest["db_filename"]
            if not db_file.exists():
                raise BackupIntegrityError(f"Database file '{manifest['db_filename']}' missing in archive")

            actual_db_sha = _sha256_file(db_file)
            if actual_db_sha != manifest["db_sha256"]:
                raise BackupIntegrityError(
                    f"Database checksum mismatch: expected {manifest['db_sha256']}, got {actual_db_sha}"
                )

            # SQLite PRAGMA check
            conn = sqlite3.connect(db_file)
            try:
                check = conn.execute("PRAGMA integrity_check").fetchone()[0]
                if check != "ok":
                    raise BackupIntegrityError(f"Database PRAGMA integrity_check failed: {check}")
            finally:
                conn.close()

            # Verify artifacts
            artifacts_dir = staging / "artifacts"
            for art_id, meta in manifest.get("artifacts", {}).items():
                art_file = artifacts_dir / meta["storage_key"]
                if not art_file.exists():
                    raise BackupIntegrityError(f"Artifact file '{meta['storage_key']}' missing in archive")
                art_sha = _sha256_file(art_file)
                if art_sha != meta["sha256"]:
                    raise BackupIntegrityError(
                        f"Artifact '{art_id}' checksum mismatch: expected {meta['sha256']}, got {art_sha}"
                    )

            return {
                "valid": True,
                "manifest_version": manifest["manifest_version"],
                "created_at": manifest["created_at"],
                "schema_version": manifest["schema_version"],
                "db_size_bytes": manifest["db_size_bytes"],
                "total_artifacts": manifest["total_artifacts"],
            }

    def restore_backup(
        self,
        backup_archive: Path | str,
        target_db_path: Path | str,
        target_artifacts_dir: Path | str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Restore database and artifacts from a validated backup archive with consistency check."""
        target_db_path = Path(target_db_path).resolve()
        target_artifacts_dir = (
            Path(target_artifacts_dir).resolve() if target_artifacts_dir else (target_db_path.parent / "artifacts")
        )

        if target_db_path.exists() and not overwrite:
            raise FileExistsError(f"Target database file already exists: {target_db_path}")

        # 1. Verify archive integrity first
        verification = self.verify_backup(backup_archive)

        with tempfile.TemporaryDirectory(prefix="agentcf_restore_") as tmp_dir:
            staging = Path(tmp_dir)
            with tarfile.open(backup_archive, "r:gz") as tar:
                tar.extractall(staging)

            manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
            db_file = staging / manifest["db_filename"]

            # 2. Deploy database
            target_db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_file, target_db_path)

            # 3. Deploy artifacts
            target_artifacts_dir.mkdir(parents=True, exist_ok=True)
            for art_id, meta in manifest.get("artifacts", {}).items():
                src_art = staging / "artifacts" / meta["storage_key"]
                dest_art = target_artifacts_dir / meta["storage_key"]
                dest_art.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_art, dest_art)

            # 4. Perform post-restore database reconciliation and foreign-key audit
            conn = sqlite3.connect(target_db_path)
            conn.row_factory = sqlite3.Row
            try:
                # PRAGMA checks
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
                if fk_violations:
                    raise BackupIntegrityError(f"Restored database foreign key violations: {len(fk_violations)}")

                counts = {
                    "workspaces": conn.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0],
                    "projects": conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
                    "processes": conn.execute("SELECT COUNT(*) FROM processes").fetchone()[0],
                    "tasks": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
                    "process_runs": conn.execute("SELECT COUNT(*) FROM process_runs").fetchone()[0],
                    "task_runs": conn.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0],
                    "attempts": conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
                    "artifacts": conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
                    "audit_events": conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
                }

                # Verify orphan run relations
                orphan_tasks = conn.execute(
                    "SELECT COUNT(*) FROM task_runs tr LEFT JOIN process_runs pr ON pr.id=tr.run_id WHERE pr.id IS NULL"
                ).fetchone()[0]
                if orphan_tasks > 0:
                    raise BackupIntegrityError(f"Restored database has {orphan_tasks} orphan task runs")

                orphan_attempts = conn.execute(
                    "SELECT COUNT(*) FROM attempts a LEFT JOIN task_runs tr ON tr.id=a.task_run_id WHERE tr.id IS NULL"
                ).fetchone()[0]
                if orphan_attempts > 0:
                    raise BackupIntegrityError(f"Restored database has {orphan_attempts} orphan attempts")

                orphan_artifacts = conn.execute(
                    "SELECT COUNT(*) FROM artifacts a LEFT JOIN attempts att ON att.id=a.attempt_id WHERE att.id IS NULL"
                ).fetchone()[0]
                if orphan_artifacts > 0:
                    raise BackupIntegrityError(f"Restored database has {orphan_artifacts} orphan artifacts")

            finally:
                conn.close()

            return {
                "restored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "manifest_version": manifest["manifest_version"],
                "schema_version": manifest["schema_version"],
                "integrity_check": integrity,
                "counts": counts,
                "verification": verification,
            }
