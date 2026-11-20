"""Short, explicit SQLite transactions and ordered SQL migrations."""

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import sqlite3


class MigrationError(RuntimeError):
    """The database and available migration history are incompatible."""


class Database:
    def __init__(
        self,
        path: Path | str,
        busy_timeout_ms: int = 5000,
        migrations_path: Path | None = None,
    ) -> None:
        if str(path) == ":memory:":
            raise ValueError("A persistent SQLite file is required")
        if busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms must be nonnegative")
        self.path = Path(path).resolve()
        self.busy_timeout_ms = busy_timeout_ms
        self.migrations_path = migrations_path or Path(__file__).resolve().parents[4] / "migrations"

    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[sqlite3.Connection]:
        if not read_only:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path.as_uri() + "?mode=ro" if read_only else self.path,
            timeout=self.busy_timeout_ms / 1000,
            isolation_level=None,
            uri=read_only,
        )
        connection.row_factory = sqlite3.Row
        connection.create_function("cf_delete_allowed", 2, lambda table, rowid: 0)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
            if not read_only:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = FULL")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.execute("COMMIT")
            except BaseException:
                connection.execute("ROLLBACK")
                raise

    def migrate(self, target_version: int | None = None) -> int:
        migrations = sorted(self.migrations_path.glob("[0-9][0-9][0-9]_*.sql"))
        if not migrations:
            raise MigrationError("No SQLite migrations found")
        versions = [int(path.name.split("_", 1)[0]) for path in migrations]
        if versions != list(range(1, len(versions) + 1)):
            raise MigrationError("Migration files must have contiguous versions starting at 1")
        target = target_version if target_version is not None else versions[-1]
        if target not in range(0, versions[-1] + 1):
            raise MigrationError("Unknown target schema version")
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
                "sha256 TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT "
                "(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))) STRICT"
            )
            applied = connection.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
            if [row["version"] for row in applied] != list(range(1, len(applied) + 1)):
                raise MigrationError("Database migration history has gaps")
            if len(applied) > len(migrations):
                raise MigrationError("Database schema is newer than this Server")
            for row, path in zip(applied, migrations):
                if row["name"] != path.name or row["sha256"] != sha256(path.read_bytes()).hexdigest():
                    raise MigrationError("An applied migration was modified")
            current = len(applied)
            if connection.execute("PRAGMA user_version").fetchone()[0] != current:
                raise MigrationError("SQLite user_version and migration history disagree")
            if target < current:
                raise MigrationError("Downgrade is not supported")
            for version, path in zip(versions, migrations):
                if not current < version <= target:
                    continue
                sql = ""
                for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
                    sql += line
                    if sqlite3.complete_statement(sql):
                        connection.execute(sql)
                        sql = ""
                if sql.strip():
                    raise MigrationError(f"Incomplete SQL in {path.name}")
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, sha256) VALUES (?, ?, ?)",
                    (version, path.name, sha256(path.read_bytes()).hexdigest()),
                )
                connection.execute(f"PRAGMA user_version = {version}")
            return target

    def schema_version(self) -> int:
        with self.connect() as connection:
            return connection.execute("PRAGMA user_version").fetchone()[0]

    def health(self) -> dict[str, int | str]:
        # A health request must not recreate an absent DB or repair a replacement.
        with self.connect(read_only=True) as connection:
            migrations = sorted(self.migrations_path.glob("[0-9][0-9][0-9]_*.sql"))
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if not migrations or version != len(migrations):
                raise MigrationError("Business database schema is not current")
            required_tables = {
                "schema_migrations", "workspaces", "projects", "processes", "process_versions",
                "tasks", "dependencies", "runners", "runner_sessions", "process_runs",
                "task_runs", "attempts", "execution_grants", "receipts", "engine_inbox",
                "run_events", "audit_events", "engine_outbox", "artifacts",
            }
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not required_tables <= tables:
                raise MigrationError("Business database is missing required tables")
            applied = connection.execute("SELECT version,name,sha256 FROM schema_migrations ORDER BY version").fetchall()
            if len(applied) != len(migrations):
                raise MigrationError("Business database migration history is incomplete")
            for expected_version, (row, path) in enumerate(zip(applied, migrations), start=1):
                if (
                    row["version"] != expected_version
                    or row["name"] != path.name
                    or row["sha256"] != sha256(path.read_bytes()).hexdigest()
                ):
                    raise MigrationError("Business database migration history is incompatible")
            return {
                "schema_version": version,
                "foreign_keys": connection.execute("PRAGMA foreign_keys").fetchone()[0],
                "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
            }
