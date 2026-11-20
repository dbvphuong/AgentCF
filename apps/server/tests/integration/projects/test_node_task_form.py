from copy import deepcopy

import pytest

from test_project_web import client, setup_project, definition


def configure_model(client, adapter="antigravity"):
    response = client.post("/v1/settings/ai-tool-models", json={"id": "node-model", "name": "Node model", "tool_id": adapter,
        "model_identifier": "exact-node-model"})
    assert response.status_code == 201, response.text


def save_graph(client, graph):
    _, process = setup_project(client)
    path = f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    response = client.put(path, json={"revision": 1, "definition": graph})
    assert response.status_code == 200, response.text
    return process, path


def test_node_model_override_and_natural_language_task_are_published_without_changing_agent(client):
    configure_model(client)
    graph = definition()
    graph["tasks"][0].update(instructions="done", runtime={"adapter": "antigravity", "model_id": "exact-node-model", "tool_model_id": "node-model"})
    process, path = save_graph(client, graph)
    response = client.post(path + "/publish", json={"revision": 2})
    assert response.status_code == 200, response.text
    published = response.json()["versions"][0]
    node = published["definition"]["tasks"][0]
    assert node["instructions"] == "done"
    assert node["runtime"]["model_id"] == "exact-node-model"
    assert node["agent_snapshot"]["model_id"] == "m"
    assert client.get("/v1/agents/a").json()["model_id"] == "m"
    before = deepcopy(published)
    client.patch("/v1/settings/ai-tool-models/node-model", json={"model_identifier": "changed-after-publish"}).raise_for_status()
    assert client.get(f"/v1/processes/{process['id']}").json()["versions"][0] == before


@pytest.mark.parametrize("bad", ["wrong_runtime", "wrong_id", "disabled_model", "disabled_provider", "missing_model"])
def test_node_model_override_is_validated_on_server(client, bad):
    configure_model(client)
    graph = definition()
    runtime = {"adapter": "antigravity", "model_id": "exact-node-model", "tool_model_id": "node-model"}
    if bad == "wrong_runtime": runtime["adapter"] = "codex"
    if bad == "wrong_id": runtime["model_id"] = "wrong"
    if bad == "missing_model": runtime["tool_model_id"] = "missing"
    if bad == "disabled_model": client.patch("/v1/settings/ai-tool-models/node-model", json={"status": "disabled"})
    if bad == "disabled_provider": client.patch("/v1/settings/providers/p", json={"status": "disabled"})
    graph["tasks"][0]["runtime"] = runtime
    _, path = save_graph(client, graph)
    assert client.post(path + "/publish", json={"revision": 2}).status_code == (404 if bad == "missing_model" else 422)


def test_legacy_api_model_runtime_binding_is_not_a_cli_model(client):
    assert client.patch("/v1/settings/models/m", json={"runtime_adapter": "antigravity"}).json()["runtime_adapter"] == "antigravity"
    assert client.patch("/v1/settings/models/m", json={"runtime_adapter": None}).json()["runtime_adapter"] is None
    cli_ids = {m["id"] for m in client.get("/v1/settings/ai-tool-models").json()}
    assert "m" not in cli_ids
