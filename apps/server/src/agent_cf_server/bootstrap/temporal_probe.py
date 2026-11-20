"""Operate the no-side-effect Temporal infrastructure persistence probe."""

import argparse
import asyncio
import json
import sys
from datetime import timedelta

from temporalio.api.enums.v1 import EventType
from temporalio.common import WorkflowIDReusePolicy

from agent_cf_server.bootstrap.config import load_settings
from agent_cf_server.infrastructure.runs.temporal.connection import connect_temporal
from agent_cf_server.infrastructure.runs.temporal.foundation_probe import (
    FoundationPersistenceProbe,
)


async def execute(command: str, workflow_id: str, marker: str) -> dict[str, object]:
    settings = load_settings()
    if not settings.temporal_enabled:
        raise ValueError("Temporal is disabled in Server configuration")
    client = await connect_temporal(
        settings.temporal_address,
        settings.temporal_namespace,
        settings.request_timeout_seconds,
    )
    if command == "start":
        handle = await client.start_workflow(
            FoundationPersistenceProbe.run,
            marker,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            execution_timeout=timedelta(days=1),
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        )
        return {"workflow_id": handle.id, "run_id": handle.result_run_id, "accepted": True}
    handle = client.get_workflow_handle(workflow_id)
    if command == "inspect":
        description = await handle.describe()
        state = await handle.query(FoundationPersistenceProbe.snapshot)
        return {
            "workflow_id": workflow_id,
            "run_id": description.run_id,
            "status": description.status.name if description.status else "UNKNOWN",
            "snapshot": state,
        }
    if command == "finish":
        await handle.signal(FoundationPersistenceProbe.finish)
        return {"workflow_id": workflow_id, "signal_accepted": True}
    if command == "result":
        return {"workflow_id": workflow_id, "result": await handle.result()}
    history = await handle.fetch_history()
    return {
        "workflow_id": workflow_id,
        "events": [
            {"id": event.event_id, "type": EventType.Name(event.event_type)}
            for event in history.events
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "inspect", "finish", "result", "history"))
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--marker", default="foundation-persistence-check")
    args = parser.parse_args()
    if not args.workflow_id.strip() or len(args.workflow_id) > 128:
        parser.error("workflow-id must contain 1..128 characters")
    if not args.marker.strip() or len(args.marker) > 128:
        parser.error("marker must contain 1..128 characters and must not contain secrets")

    async def bounded() -> dict[str, object]:
        settings = load_settings()
        return await asyncio.wait_for(
            execute(args.command, args.workflow_id, args.marker),
            timeout=settings.request_timeout_seconds * 2,
        )

    try:
        result = asyncio.run(bounded())
    except (Exception, KeyboardInterrupt) as error:
        print(
            f"Temporal probe failed ({type(error).__name__}): {error}. "
            "A timed-out request does not prove the workflow stopped; inspect the same ID.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
