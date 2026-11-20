"""Verify process session_mode configuration and assignment dispatch."""
from test_project_web import client, definition, setup_project


def test_session_mode_saved_and_frozen_into_snapshot(client):
    project, process = setup_project(client)
    pid = process["id"]

    # 1. Default session_mode is shared_per_tool
    config = client.get(f"/v1/processes/{pid}/configuration").json()
    assert config["definition"].get("session_mode") == "shared_per_tool"

    # 2. Update to isolated
    graph = definition()
    graph["session_mode"] = "isolated"
    resp = client.put(f"/v1/processes/{pid}/configuration", json={
        "definition": graph, "expected_token": config["configuration_token"],
    })
    assert resp.status_code == 200
    assert resp.json()["definition"]["session_mode"] == "isolated"

    # 3. Create run and check snapshot
    run_resp = client.post(f"/v1/processes/{pid}/runs", json={"input": {}}, headers={"Idempotency-Key": "run-isolated"})
    assert run_resp.status_code == 202
    run_data = run_resp.json()
    version_id = run_data["process_version_id"]

    p_detail = client.get(f"/v1/processes/{pid}").json()
    ver = next(v for v in p_detail["versions"] if v["id"] == version_id)
    assert ver["definition"]["session_mode"] == "isolated"
    assert ver["definition"]["tasks"][0]["session_mode"] == "isolated"


def test_session_mode_default_shared_per_tool_in_snapshot(client):
    project, process = setup_project(client)
    pid = process["id"]

    config = client.get(f"/v1/processes/{pid}/configuration").json()
    graph = definition()
    resp = client.put(f"/v1/processes/{pid}/configuration", json={
        "definition": graph, "expected_token": config["configuration_token"],
    })
    assert resp.status_code == 200

    run_resp = client.post(f"/v1/processes/{pid}/runs", json={"input": {}}, headers={"Idempotency-Key": "run-shared"})
    assert run_resp.status_code == 202
    run_data = run_resp.json()
    version_id = run_data["process_version_id"]

    p_detail = client.get(f"/v1/processes/{pid}").json()
    ver = next(v for v in p_detail["versions"] if v["id"] == version_id)
    assert ver["definition"]["session_mode"] == "shared_per_tool"
    assert ver["definition"]["tasks"][0]["session_mode"] == "shared_per_tool"
