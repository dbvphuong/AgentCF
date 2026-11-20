# Temporal local development

The Service and worker are separate processes. This is the BASE-003 infrastructure check, not production deployment, the Process DAG interpreter or PC execution.

Install the official [Temporal CLI](https://docs.temporal.io/cli), then run from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infra/temporal/start-dev.ps1
```

The launcher binds the Service to loopback, defaults to port 7233 and UI port 8233, and persists engine history at `runtime/temporal/temporal.sqlite`, outside Git. It runs in the foreground; Ctrl+C stops the Service. Pass `-TemporalBinary <path>` for a CLI not on PATH or `-DatabasePath <absolute-path>` for another engine data directory. Never pass the business SQLite file. It is not necessary to install a Windows Service or change the user's PowerShell policy. The process-specific `-ExecutionPolicy Bypass` affects this invocation only.

After installing the Server package/dependencies, use another terminal:

```powershell
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.worker
```

Both worker and probe read Server config. The worker polls the configured task queue and registers only `AgentCFFoundationPersistenceProbeV1`. It does not read or write the business DB, call a runtime, spawn a tool, or implement production Run endpoints.

Without a Service, the SDK compatibility checks still run locally:

```powershell
.venv/Scripts/python.exe -m pytest apps/server/tests/unit/infrastructure/runs/temporal -q
```

They prepare the Workflow sandbox on the installed Python/SDK, check connection timeout, and ensure disabled Temporal configuration is rejected before opening a connection. They do not prove Service persistence or restart.

Operate the probe from a third terminal:

```powershell
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.temporal_probe start --workflow-id foundation/manual-1 --marker restart-check
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.temporal_probe inspect --workflow-id foundation/manual-1
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.temporal_probe history --workflow-id foundation/manual-1
```

Keep the probe waiting, stop the worker and Service, restart them with the same DB path/config, then run `inspect` and `history` again. The marker and original Run ID must remain. Finish and read the result:

```powershell
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.temporal_probe finish --workflow-id foundation/manual-1
.venv/Scripts/python.exe -m agent_cf_server.bootstrap.temporal_probe result --workflow-id foundation/manual-1
```

Workflow IDs cannot be reused after completion; choose a new ID for another check. Marker is a short non-sensitive test value stored in engine history. Probe commands have a finite timeout; timeout does not imply the accepted workflow stopped.

The opt-in integration test creates its own workflow/task-queue IDs and worker instances; only a Service is required:

```powershell
$env:AGENT_CF_TEMPORAL_INTEGRATION = '1'
.venv/Scripts/python.exe -m pytest apps/server/tests/integration/temporal -q
Remove-Item Env:AGENT_CF_TEMPORAL_INTEGRATION
```

This test proves worker restart/replay, durable result/history reads and duplicate Workflow ID rejection. The manual Service restart check is separate. Neither proves application outbox dispatch, human Continue, recovery of PC processes or exactly-once external side effects.
