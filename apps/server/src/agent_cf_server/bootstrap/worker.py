"""Run the independent Temporal foundation worker in the foreground."""

import asyncio
import logging
from datetime import timedelta

from temporalio.worker import Worker

from agent_cf_server.bootstrap.config import load_settings
from agent_cf_server.infrastructure.runs.temporal.connection import connect_temporal
from agent_cf_server.infrastructure.runs.temporal.foundation_probe import (
    FoundationPersistenceProbe,
)


async def run_worker() -> None:
    settings = load_settings()
    if not settings.temporal_enabled:
        raise ValueError("Temporal is disabled in Server configuration")
    client = await connect_temporal(
        settings.temporal_address,
        settings.temporal_namespace,
        settings.request_timeout_seconds,
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[FoundationPersistenceProbe],
        graceful_shutdown_timeout=timedelta(seconds=5),
    )
    logging.getLogger(__name__).info(
        "Temporal foundation worker polling task queue %s", settings.temporal_task_queue
    )
    await worker.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
