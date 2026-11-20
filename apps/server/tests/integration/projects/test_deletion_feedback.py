"""Deletion blockers identify real names and preserve every existing guard."""

import pytest

from test_project_web import client, setup_project, definition
from test_project_deletion import published, history
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.settings.repository import SettingsRepository
from agent_cf_server.infrastructure.agents.repository import AgentRepository


def detail(response, status=409):
    assert response.status_code == status, response.text
    message = response.json()["detail"]
    assert isinstance(message, str)
    assert "FOREIGN KEY" not in message and "Archive instead" not in message
    return message


def test_provider_lists_models_by_name_including_disabled_and_rolls_back(client):
    repo = SettingsRepository(client.app.state.database)
    repo.create_provider("opaque-provider-id", "Nhà cung cấp thử", "custom", "http://localhost", api_key="secret-never-in-error")
    repo.create_model("opaque-model-one", "opaque-provider-id", "Model đang bật", "exact-one")
    repo.create_model("opaque-model-two", "opaque-provider-id", "Model đã ngừng", "exact-two", status="disabled")
    message = detail(client.delete("/v1/settings/providers/opaque-provider-id"))
    for name in ("Nhà cung cấp thử", "Model đang bật", "Model đã ngừng", "Models API"):
        assert name in message
    for hidden in ("opaque-provider-id", "opaque-model-one", "opaque-model-two", "secret-never-in-error"):
        assert hidden not in message
    assert repo.get_provider("opaque-provider-id")["name"] == "Nhà cung cấp thử"
    repo.delete_model("opaque-model-one")
    repo.delete_model("opaque-model-two")
    assert client.delete("/v1/settings/providers/opaque-provider-id").status_code == 204


@pytest.mark.parametrize("kind", ["models", "roles"])
def test_api_model_and_role_identify_agents_and_allow_delete_after_unlink(client, kind):
    repo = SettingsRepository(client.app.state.database)
    agents = AgentRepository(client.app.state.database)
    repo.create_model("opaque-model-id", "p", "Model viết bài", "exact")
    repo.create_role("opaque-role-id", "Người biên tập")
    agents.create_agent("opaque-agent-id", "Biên tập viên", "opaque-role-id", "opaque-model-id", status="archived")
    target = "opaque-model-id" if kind == "models" else "opaque-role-id"
    name = "Model viết bài" if kind == "models" else "Người biên tập"
    message = detail(client.delete(f"/v1/settings/{kind}/{target}"))
    assert name in message and "Biên tập viên" in message and "Agent điều phối" in message
    assert target not in message and "opaque-agent-id" not in message
    agents.delete_agent("opaque-agent-id")
    assert client.delete(f"/v1/settings/{kind}/{target}").status_code == 204


def test_many_model_references_are_named_and_omissions_are_explicit(client):
    repo = SettingsRepository(client.app.state.database)
    repo.create_provider("opaque-many-provider", "Provider nhiều model", "custom", "http://localhost")
    for i in range(10):
        repo.create_model(f"opaque-many-model-{i}", "opaque-many-provider", f"Model {i:02}", f"model-{i}")
    message = detail(client.delete("/v1/settings/providers/opaque-many-provider"))
    assert "Model 00" in message and "Model 07" in message and "và 2 mục khác" in message
    assert "opaque-many-model" not in message


@pytest.mark.parametrize("kind", ["skills", "agents"])
def test_catalog_blocker_identifies_project_process_and_node(client, kind):
    project, process = setup_project(client)
    version = process["versions"][0]["id"]
    client.put(f"/v1/processes/{process['id']}/versions/{version}", json={"revision": 1, "definition": definition()}).raise_for_status()
    path = "/v1/skills/s" if kind == "skills" else "/v1/agents/a"
    message = detail(client.delete(path))
    for name in (project["name"], process["name"], "First", "cấu hình Process"):
        assert name in message
    assert project["id"] not in message and process["id"] not in message


@pytest.mark.parametrize("kind", ["projects", "processes"])
@pytest.mark.parametrize("status", ["queued", "running", "reconciling", "cancelling"])
def test_run_blocker_names_process_project_time_and_state(client, kind, status):
    project, process, version = published(client)
    run = client.post("/v1/runs", json={"process_version_id": version}, headers={"Idempotency-Key": "feedback-run"}).json()
    with client.app.state.database.transaction() as conn:
        conn.execute("UPDATE process_runs SET status=?,created_at='2026-11-20T01:02:03Z' WHERE id=?", (status, run["id"]))
    target = project["id"] if kind == "projects" else process["id"]
    message = detail(client.delete(f"/v1/{kind}/{target}"), 422)
    for text in (project["name"], process["name"], "20/11/2026 08:02:03", "Runs"):
        assert text in message
    for hidden in (run["id"], project["id"], process["id"], version):
        assert hidden not in message
    assert client.get(f"/v1/{kind}/{target}").status_code == 200


def test_cli_model_blocker_identifies_saved_version_and_project(client):
    project, process, version = published(client)
    graph = client.get(f"/v1/processes/{process['id']}").json()["versions"][0]["definition"]
    model = graph["tasks"][0]["runtime"]["tool_model_id"]
    model_name = client.get(f"/v1/settings/ai-tool-models/{model}").json()["name"]
    message = detail(client.delete(f"/v1/settings/ai-tool-models/{model}"))
    for text in (model_name, project["name"], process["name"], "v1", "tắt sử dụng"):
        assert text in message
    assert model not in message and version not in message


def test_tool_blocker_identifies_both_skill_version_and_agent(client):
    client.post("/v1/skills/tools", json={"id": "opaque-tool-id", "name": "Tìm kiếm tài liệu"}).raise_for_status()
    client.post("/v1/skills/s/versions", json={"id": "opaque-skill-version", "instructions": "Use search", "tool_ids": ["opaque-tool-id"]}).raise_for_status()
    client.patch("/v1/agents/a", json={"allowed_tool_ids": ["opaque-tool-id"]}).raise_for_status()
    message = detail(client.delete("/v1/skills/tools/opaque-tool-id"))
    for text in ("Tìm kiếm tài liệu", "Any configured skill", "v2", "PM", "Allowed tools"):
        assert text in message
    assert "opaque-tool-id" not in message and "opaque-skill-version" not in message
    assert client.get("/v1/skills/tools/opaque-tool-id").status_code == 200


@pytest.mark.parametrize("referenced", [False, True])
def test_robot_blocker_names_version_or_process_without_archive_advice(client, referenced):
    robot = client.post("/v1/robots", json={"id": "opaque-robot-id", "name": "Robot đọc tài liệu"}).json()
    version = client.post(f"/v1/robots/{robot['id']}/versions", json={"entrypoint": "python main.py", "ready_to_use": True}).json()
    if referenced:
        project, process, _ = published(client)
        graph = {"definition_format_version": "1", "interpreter_version": "dag-v1", "dependencies": [], "tasks": [
            {"id": "opaque-task-id", "task_key": "reader", "name": "Đọc tài liệu", "kind": "robot", "robot_version_id": version["id"]},
        ]}
        ProcessRepository(client.app.state.database).store_published(
            workspace_id=project["workspace_id"], project_id=project["id"], process_id=process["id"],
            version_id="opaque-process-version", version_number=2, definition=graph, snapshot_sha256="d" * 64,
        )
    message = detail(client.delete(f"/v1/robots/{robot['id']}"))
    assert "Robot đọc tài liệu" in message and "v" in message
    assert robot["id"] not in message and version["id"] not in message and "Archive" not in message
    if referenced:
        for name in ("Đọc tài liệu", process["name"], project["name"], "v2"):
            assert name in message
        assert "opaque-task-id" not in message and "opaque-process-version" not in message
    else:
        assert "v1 được phát hành" in message and "chưa hỗ trợ xóa" in message


def test_published_skill_version_error_has_name_and_version(client):
    message = detail(client.delete("/v1/skills/s/versions/sv"))
    assert "Any configured skill" in message and "v1" in message and "bất biến" in message


@pytest.mark.parametrize("kind", ["skills", "agents"])
def test_unfinished_snapshot_still_names_blocking_process_after_configuration_changes(client, kind):
    project, process, version = published(client)
    client.post("/v1/runs", json={"process_version_id": version}, headers={"Idempotency-Key": "snapshot-feedback"}).raise_for_status()
    with client.app.state.database.transaction() as conn:
        conn.execute('UPDATE processes SET configuration_json=\'{"tasks":[]}\' WHERE id=?', (process["id"],))
    path = "/v1/skills/s" if kind == "skills" else "/v1/agents/a"
    message = detail(client.delete(path))
    for name in (project["name"], process["name"], "snapshot của Run chưa kết thúc", "dừng Run"):
        assert name in message


@pytest.mark.parametrize("kind", ["projects", "processes"])
def test_unsettled_pc_work_names_pc_and_finished_run(client, kind):
    project, process, run, _ = history(client)
    with client.app.state.database.transaction() as conn:
        conn.execute("UPDATE runners SET name='PC biên tập' WHERE id=?", (run,))
        conn.execute(
            "INSERT INTO attempts(id,task_run_id,run_id,runner_id,session_id,generation,status,claimed_at,execution_deadline_at) "
            "SELECT 'opaque-unsettled-attempt',task_run_id,run_id,runner_id,session_id,generation+1,'reconciling',claimed_at,execution_deadline_at "
            "FROM attempts WHERE run_id=?", (run,),
        )
    target = project["id"] if kind == "projects" else process["id"]
    message = detail(client.delete(f"/v1/{kind}/{target}"), 422)
    for name in ("PC biên tập", project["name"], process["name"], "chưa xác nhận", "Client"):
        assert name in message
    assert run not in message
