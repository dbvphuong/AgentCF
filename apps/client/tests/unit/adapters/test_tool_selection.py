import pytest

from agent_cf_client.execution.task_worker import TaskExecutionWorker


def test_explicit_tool_is_not_overridden_by_model_or_provider_names():
    worker = TaskExecutionWorker.__new__(TaskExecutionWorker)
    worker.codex_adapter = object()
    worker.antigravity_adapter = object()
    assert worker.select_adapter({"runtime": {"adapter": "codex", "model_id": "gemini", "provider": "antigravity"}}) is worker.codex_adapter
    assert worker.select_adapter({"runtime": {"adapter": "antigravity", "model_id": "gpt"}}) is worker.antigravity_adapter
    for runtime in ({}, {"adapter": "other"}, {"model_id": "gemini"}):
        with pytest.raises(ValueError):
            worker.select_adapter({"runtime": runtime})
