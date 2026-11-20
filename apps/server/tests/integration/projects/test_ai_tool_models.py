from test_project_web import client, setup_project, definition


def test_cli_catalog_is_separate_and_scoped_to_tool(client):
    defaults = client.get("/v1/settings/ai-tool-models").json()
    assert {m["tool_id"] for m in defaults} == {"codex", "antigravity"}
    assert not any(m["id"] == "m" for m in defaults)
    payload = {"id": "agy-new", "tool_id": "antigravity", "name": "My model", "model_identifier": "exact-new"}
    assert client.post("/v1/settings/ai-tool-models", json=payload).status_code == 201
    duplicate = client.post("/v1/settings/ai-tool-models", json={**payload, "id": "another"})
    assert duplicate.status_code == 409
    assert client.post("/v1/settings/ai-tool-models", json={**payload, "id": "codex-new", "tool_id": "codex"}).status_code == 201
    agy = client.get("/v1/settings/ai-tool-models", params={"tool_id": "antigravity", "status": "active"}).json()
    assert all(row["tool_id"] == "antigravity" and row["status"] == "active" for row in agy)
    assert client.patch("/v1/settings/ai-tool-models/agy-new", json={"status": "disabled"}).json()["status"] == "disabled"
    active = client.get("/v1/settings/ai-tool-models?status=active").json()
    assert "agy-new" not in {m["id"] for m in active}
    assert client.patch("/v1/settings/ai-tool-models/agy-new", json={"tool_id": "codex"}).status_code == 409
    assert client.patch("/v1/settings/ai-tool-models/agy-new", json={"model_identifier": "new-cli-id"}).status_code == 200
    assert client.get("/v1/settings/models/m").json()["model_identifier"] == "exact-model"
    for invalid in ({"model_identifier": "   "}, {"status": None}, {"tool_id": "unknown"}, {"provider_id": "p"}, {"model_identifier": "line\nbreak"}):
        assert client.patch("/v1/settings/ai-tool-models/agy-new", json=invalid).status_code == 422
    assert client.delete("/v1/settings/ai-tool-models/agy-new").status_code == 204
    assert client.get("/v1/settings/ai-tool-models/agy-new").status_code == 404


def test_api_only_model_cannot_be_used_for_cli_even_with_runtime_binding(client):
    client.patch("/v1/settings/models/m", json={"model_identifier": "api-only", "runtime_adapter": "antigravity"}).raise_for_status()
    project, process = setup_project(client)
    graph = definition()
    graph["tasks"][0]["runtime"] = {"adapter": "antigravity", "model_id": "api-only", "catalog_model_id": "m"}
    path = f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    client.put(path, json={"definition": graph, "revision": 1}).raise_for_status()
    assert client.post(path + "/publish", json={"revision": 2}).status_code == 422


def test_disabled_cli_model_blocks_new_runs_but_keeps_published_history(client):
    project, process = setup_project(client)
    path = f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    client.put(path, json={"definition": definition(), "revision": 1}).raise_for_status()
    published = client.post(path + "/publish", json={"revision": 2})
    published.raise_for_status()
    snapshot = published.json()["versions"][0]
    cli_id = snapshot["definition"]["tasks"][0]["runtime"]["tool_model_id"]
    assert client.delete("/v1/settings/ai-tool-models/" + cli_id).status_code == 409
    client.patch("/v1/settings/ai-tool-models/" + cli_id, json={"status": "disabled"}).raise_for_status()
    response = client.post("/v1/runs", json={"process_version_id": snapshot["id"]}, headers={"Idempotency-Key": "blocked-model"})
    assert response.status_code == 422
    assert client.get(f"/v1/processes/{process['id']}").json()["versions"][0] == snapshot
    client.patch("/v1/settings/ai-tool-models/" + cli_id, json={"status": "active", "model_identifier": "updated-cli-id"}).raise_for_status()
    run = client.post("/v1/runs", json={"process_version_id": snapshot["id"]}, headers={"Idempotency-Key": "allowed-model"})
    assert run.status_code == 202
    assert client.get(f"/v1/processes/{process['id']}").json()["versions"][0] == snapshot


def test_sync_and_check_endpoints(client):
    check = client.get("/v1/settings/ai-tool-models/check")
    assert check.status_code == 200
    res = check.json()
    assert "codex" in res and "antigravity" in res
    assert "installed" in res["codex"] and "status" in res["codex"]
    assert "installed" in res["antigravity"] and "status" in res["antigravity"]

    sync = client.post("/v1/settings/ai-tool-models/sync")
    assert sync.status_code == 200
    sync_res = sync.json()
    assert "added_count" in sync_res
    assert "total" in sync_res
    assert sync_res["total"] >= 15

    models = client.get("/v1/settings/ai-tool-models").json()
    identifiers = {m["model_identifier"] for m in models}
    assert "gpt-5.6-sol" in identifiers
    assert "gpt-5.6-terra" in identifiers
    assert "claude-sonnet-4.6-thinking" in identifiers
    assert "claude-opus-4.6-thinking" in identifiers
    assert "gemini-3.8-flash-high" in identifiers


def test_configure_tool_models_batch_toggles_active_status(client):
    # Get all codex models
    codex_models = client.get("/v1/settings/ai-tool-models", params={"tool_id": "codex"}).json()
    assert len(codex_models) >= 2
    selected_ids = [codex_models[0]["id"]]

    # Configure only the first model as active
    res = client.post("/v1/settings/ai-tool-models/configure", json={"tool_id": "codex", "active_model_ids": selected_ids})
    assert res.status_code == 200
    updated = res.json()
    for m in updated:
        if m["id"] == selected_ids[0]:
            assert m["status"] == "active"
        else:
            assert m["status"] == "disabled"

    # Process node selector query (?status=active) must only return the active model for codex
    active = client.get("/v1/settings/ai-tool-models", params={"tool_id": "codex", "status": "active"}).json()
    assert [m["id"] for m in active] == selected_ids

    # Select all models back
    all_ids = [m["id"] for m in codex_models]
    res2 = client.post("/v1/settings/ai-tool-models/configure", json={"tool_id": "codex", "active_model_ids": all_ids})
    assert res2.status_code == 200
    active2 = client.get("/v1/settings/ai-tool-models", params={"tool_id": "codex", "status": "active"}).json()
    assert len(active2) == len(codex_models)
