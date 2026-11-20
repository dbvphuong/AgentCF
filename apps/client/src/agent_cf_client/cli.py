"""Console entrypoint for local foundation checks."""

import argparse
import json
import os
import sys

from agent_cf_client.config import ClientConfig
from agent_cf_client.connection.health import HealthCheckError, check_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CF Client local foundation")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Check Server and database connectivity without acquiring work")
    check.add_argument("--server-url", help="Override AGENT_CF_CLIENT_SERVER_URL")
    check.add_argument("--timeout", type=float, help="Override AGENT_CF_CLIENT_TIMEOUT_SECONDS")

    pair_cmd = commands.add_parser("pair", help="Pair this PC with Agent CF Server using a pairing code")
    pair_cmd.add_argument("--server-url", required=True, help="Agent CF Server URL (e.g. http://127.0.0.1:8000)")
    pair_cmd.add_argument("--code", required=True, help="Pairing code from operator")
    pair_cmd.add_argument("--credentials-file", help="Path to save runner credentials")
    desktop = commands.add_parser("desktop", help="Open the general CF Client desktop application")
    desktop.add_argument("--connect", help="Validated agentcf://connect link")
    desktop.add_argument("--background", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "desktop":
        from agent_cf_client.desktop.entry import main as desktop_main
        options = ["--desktop"]
        if args.connect:
            options += ["--connect", args.connect]
        if args.background:
            options += ["--background"]
        return desktop_main(options)

    if args.command == "pair":
        from pathlib import Path
        from agent_cf_client.connection.client_session import ClientSessionManager
        cred_path = Path(args.credentials_file) if args.credentials_file else None
        manager = ClientSessionManager(credentials_path=cred_path)
        try:
            res = manager.pair(server_url=args.server_url, pairing_code=args.code)
            print(json.dumps({"status": "ok", "paired": True, "runner_id": res["runner_id"]}))
            return 0
        except Exception as exc:
            print(f"Pairing error: {exc}", file=sys.stderr)
            return 1
    try:
        environment = dict(os.environ)
        if args.server_url is not None:
            environment["AGENT_CF_CLIENT_SERVER_URL"] = args.server_url
        if args.timeout is not None:
            environment["AGENT_CF_CLIENT_TIMEOUT_SECONDS"] = str(args.timeout)
        config = ClientConfig.from_environment(environment)
        health = check_server(config)
    except (ValueError, HealthCheckError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "ok",
        "database": {"schema_version": health.schema_version},
        "temporal": {"configured": health.temporal_configured},
    }))
    return 0
