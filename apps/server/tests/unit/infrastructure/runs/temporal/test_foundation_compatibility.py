"""SDK compatibility and bounded startup checks; no Service or network required."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from temporalio import workflow
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from agent_cf_server.bootstrap import temporal_probe, worker
from agent_cf_server.infrastructure.runs.temporal import connection
from agent_cf_server.infrastructure.runs.temporal.foundation_probe import (
    FoundationPersistenceProbe,
)


def test_probe_prepares_inside_python_workflow_sandbox() -> None:
    async def prepare() -> None:
        definition = workflow._Definition.must_from_class(FoundationPersistenceProbe)
        SandboxedWorkflowRunner().prepare_workflow(definition)

    asyncio.run(prepare())


def test_connect_timeout_does_not_hang_startup(monkeypatch) -> None:
    async def pending_connection(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(connection.Client, "connect", pending_connection)
    with pytest.raises(TimeoutError):
        asyncio.run(connection.connect_temporal("127.0.0.1:7233", "default", 0.01))


def test_disabled_worker_fails_before_opening_connection(monkeypatch) -> None:
    connect = AsyncMock()
    monkeypatch.setattr(worker, "load_settings", lambda: SimpleNamespace(temporal_enabled=False))
    monkeypatch.setattr(worker, "connect_temporal", connect)
    with pytest.raises(ValueError, match="Temporal is disabled"):
        asyncio.run(worker.run_worker())
    connect.assert_not_called()


def test_disabled_probe_exits_with_context_without_connecting(monkeypatch, capsys) -> None:
    connect = AsyncMock()
    settings = SimpleNamespace(temporal_enabled=False, request_timeout_seconds=1)
    monkeypatch.setattr(temporal_probe, "load_settings", lambda: settings)
    monkeypatch.setattr(temporal_probe, "connect_temporal", connect)
    monkeypatch.setattr(
        "sys.argv", ["temporal_probe", "start", "--workflow-id", "foundation/disabled"]
    )
    assert temporal_probe.main() == 1
    assert "Temporal is disabled" in capsys.readouterr().err
    connect.assert_not_called()
