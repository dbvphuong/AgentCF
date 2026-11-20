#!/usr/bin/env python3
"""CLI utility for Agent CF database and artifact backup, verification, and restore (DATA-002)."""

import argparse
import json
from pathlib import Path
import sys

# Ensure server src is in path
ROOT = Path(__file__).resolve().parents[3]
SERVER_SRC = ROOT / "apps" / "server" / "src"
if str(SERVER_SRC) not in sys.path:
    sys.path.insert(0, str(SERVER_SRC))

from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.persistence.backup import BackupManager, BackupError


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent CF SQLite & Artifacts Backup and Restore Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Backup command
    backup_parser = subparsers.add_parser("backup", help="Create point-in-time backup bundle")
    backup_parser.add_argument("--db-path", default=str(ROOT / "data" / "agent_cf.sqlite"), help="Path to source SQLite database")
    backup_parser.add_argument("--artifacts-dir", default=None, help="Path to artifacts storage directory")
    backup_parser.add_argument("-o", "--output", required=True, help="Destination backup archive path (.tar.gz)")

    # 2. Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify backup archive integrity")
    verify_parser.add_argument("-i", "--input", required=True, help="Backup archive to verify (.tar.gz)")

    # 3. Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database and artifacts from backup")
    restore_parser.add_argument("-i", "--input", required=True, help="Backup archive to restore (.tar.gz)")
    restore_parser.add_argument("--target-db", required=True, help="Path to target restored SQLite database")
    restore_parser.add_argument("--target-artifacts", default=None, help="Path to target artifacts directory")
    restore_parser.add_argument("--overwrite", action="store_true", help="Overwrite target database if it exists")

    args = parser.parse_args()

    try:
        if args.command == "backup":
            db = Database(args.db_path)
            mgr = BackupManager(db, artifacts_dir=args.artifacts_dir)
            out_file = mgr.create_backup(args.output)
            print(json.dumps({"status": "success", "backup_file": str(out_file)}, indent=2))
            return 0

        elif args.command == "verify":
            # For verification, we can initialize BackupManager with a dummy db path
            db = Database(ROOT / "data" / "dummy.sqlite")
            mgr = BackupManager(db)
            report = mgr.verify_backup(args.input)
            print(json.dumps({"status": "valid", "details": report}, indent=2))
            return 0

        elif args.command == "restore":
            db = Database(args.target_db)
            mgr = BackupManager(db)
            report = mgr.restore_backup(
                backup_archive=args.input,
                target_db_path=args.target_db,
                target_artifacts_dir=args.target_artifacts,
                overwrite=args.overwrite,
            )
            print(json.dumps({"status": "restored", "report": report}, indent=2))
            return 0

    except BackupError as err:
        print(json.dumps({"status": "error", "error": type(err).__name__, "message": str(err)}), file=sys.stderr)
        return 1
    except Exception as err:
        print(json.dumps({"status": "unexpected_error", "error": type(err).__name__, "message": str(err)}), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
