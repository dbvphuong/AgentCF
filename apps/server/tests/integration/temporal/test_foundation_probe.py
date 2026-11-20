"""Opt-in integration test against the local development Temporal Service."""

import asyncio
import os
from datetime import timedelta
from uuid import uuid4

import pytest

if os.environ.get("AGENT_CF_TEMPORAL_INTEGRATION") != "1":
    pytest.skip(
        "Set AGENT_CF_TEMPORAL_INTEGRATION=1 and start the local Temporal Service",
        allow_module_level=True,
    )

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker

from agent_cf_server.bootstrap.config import load_settings
from agent_cf_server.infrastructure.runs.temporal.foundation_probe import (
    FoundationPersistenceProbe,
)


def test_waiting_probe_replays_after_worker_restart_and_rejects_id_reuse() -> None:
    async def scenario() -> None:
        settings = load_settings()
        client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )
        workflow_id = f"foundation-test/{uuid4()}"
        queue = f"foundation-test-{uuid4()}"
        async with Worker(client, task_queue=queue, workflows=[FoundationPersistenceProbe]):
            handle = await client.start_workflow(
                FoundationPersistenceProbe.run,
                "persisted-marker",
                id=workflow_id,
                task_queue=queue,
                execution_timeout=timedelta(minutes=2),
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
            state = await handle.query(FoundationPersistenceProbe.snapshot)
            assert state == {"marker": "persisted-marker", "finish_requested": False}
            history_before_restart = await handle.fetch_history()
            assert history_before_restart.events

        # A fresh worker must rebuild state from Service history, not Python memory.
        async with Worker(client, task_queue=queue, workflows=[FoundationPersistenceProbe]):
            assert await handle.query(FoundationPersistenceProbe.snapshot) == state
            await handle.signal(FoundationPersistenceProbe.finish)
            assert await handle.result() == {"marker": "persisted-marker", "completed": True}

        new_client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )
        reopened = new_client.get_workflow_handle(workflow_id)
        assert await reopened.result() == {"marker": "persisted-marker", "completed": True}
        history_after_restart = await reopened.fetch_history()
        assert len(history_after_restart.events) > len(history_before_restart.events)
        with pytest.raises(WorkflowAlreadyStartedError):
            await new_client.start_workflow(
                FoundationPersistenceProbe.run,
                "must-not-replace-history",
                id=workflow_id,
                task_queue=queue,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )

    asyncio.run(asyncio.wait_for(scenario(), timeout=45))
