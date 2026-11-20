"""Save-and-run uses current configuration and preserves immutable Run history."""
from test_project_web import client, definition, setup_project


def save(client, pid, graph):
    config = client.get(f"/v1/processes/{pid}/configuration").json()
    response = client.put(f"/v1/processes/{pid}/configuration", json={
        "definition": graph, "expected_token": config["configuration_token"],
    })
    assert response.status_code == 200, response.text
    return response.json()


def run(client, pid, key):
    response = client.post(f"/v1/processes/{pid}/runs", json={"input": {}}, headers={"Idempotency-Key": key})
    assert response.status_code == 202, response.text
    return response.json()


def test_save_run_without_publish_and_frozen_history(client):
    project, process = setup_project(client)
    pid = process["id"]
    # Latest Skill configuration is deliberately never published.
    response = client.post("/v1/skills/s/versions", json={"id": "new-source", "instructions": "New local-tested instructions"})
    assert response.status_code == 201, response.text
    graph = definition()
    config = save(client, pid, graph)
    stale = client.put(f"/v1/processes/{pid}/configuration", json={"definition":graph,"expected_token":"empty"})
    assert stale.status_code == 409
    first = run(client, pid, "first")
    snapshot = next(v for v in client.get(f"/v1/processes/{pid}").json()["versions"] if v["id"] == first["process_version_id"])
    assert snapshot["definition"]["tasks"][0]["skill_snapshot"]["instructions"] == "New local-tested instructions"
    assert run(client, pid, "first")["id"] == first["id"]
    assert len(client.get(f"/v1/processes/{pid}").json()["versions"]) == 1
    response = client.patch("/v1/skills/s/versions/new-source", json={"instructions":"Changed instructions", "output_standards":"", "tool_ids":[]})
    assert response.status_code == 200, response.text
    second = run(client, pid, "second")
    snapshots = client.get(f"/v1/processes/{pid}").json()["versions"]
    assert next(v for v in snapshots if v["id"] == second["process_version_id"])["definition"]["tasks"][0]["skill_snapshot"]["instructions"] == "Changed instructions"
    assert next(v for v in snapshots if v["id"] == first["process_version_id"]) == snapshot
    assert client.get(f"/v1/processes/{pid}/configuration").json() == config


def test_current_schedule_uses_saved_changes(client):
    project, process = setup_project(client)
    pid = process["id"]
    graph = definition()
    save(client, pid, graph)
    response = client.post(f"/v1/processes/{pid}/schedules?project_id={project['id']}", headers={"Idempotency-Key":"schedule"}, json={"name":"Daily", "follow_current_configuration":True})
    assert response.status_code == 201, response.text
    schedule = response.json()
    graph["tasks"][0]["instructions"] = "Latest saved task"
    save(client, pid, graph)
    response = client.post(f"/v1/schedules/{schedule['id']}/trigger", headers={"Idempotency-Key":"tick"}, json={"scheduled_for":"2026-11-20T00:00:00Z"})
    assert response.status_code == 200, response.text
    current_run = client.get(f"/v1/runs/{response.json()['run_id']}").json()
    snapshots = client.get(f"/v1/processes/{pid}").json()["versions"]
    assert next(v for v in snapshots if v["id"] == current_run["process_version_id"])["definition"]["tasks"][0]["instructions"] == "Latest saved task"


def test_local_source_saved_in_skill_form_is_ready_without_publish(client):
    project, process = setup_project(client)
    pid = process["id"]
    root = r"E:\Project"
    client.patch(f"/v1/projects/{project['id']}",json={"name":project["name"],"workspace_id":project["workspace_id"],"pm_agent_id":"a","working_directory":root}).raise_for_status()
    code=client.post("/v1/pairing-codes",json={"workspace_id":project["workspace_id"],"name":"PC"}).json()["pairing_code"]
    pc=client.post("/v1/runners/pair",json={"pairing_code":code}).json()["runner_id"]
    skill=client.post("/v1/skills",json={"id":"local","name":"Local source","is_global":True,"source_path":root+r"\.agents\SKILL.md","source_runner_id":pc})
    assert skill.status_code == 201, skill.text
    graph=definition()
    for node in graph["tasks"]:
        node["skill_id"]="local"
        # Old node-level cwd is no longer an output/workspace setting in the
        # current configuration flow. The Project owns the CLI root.
        node["working_directory"]=r"E:\Old node directory"
    save(client,pid,graph)
    context=client.get(f"/v1/processes/{pid}/run-context").json()
    assert context["topic_supported"] and context["runner_id"]==pc
    response=client.post(f"/v1/processes/{pid}/runs",json={"input":{"topic_directory":root+r"\Topic 2"}},headers={"Idempotency-Key":"local"})
    assert response.status_code==202, response.text
    assert response.json()["input"]["topic_directory"]==root+r"\Topic 2"
    old_snapshot=response.json()["process_version_id"]
    snapshot=client.get(f"/v1/processes/{pid}/versions/{old_snapshot}").json()
    assert all(t["working_directory"]==root for t in snapshot["definition"]["tasks"])
    new_root=r"E:\New Project"
    client.patch(f"/v1/projects/{project['id']}",json={"name":project["name"],"workspace_id":project["workspace_id"],"pm_agent_id":"a","working_directory":new_root}).raise_for_status()
    assert client.get(f"/v1/processes/{pid}/run-context").json()["working_directory"]==new_root
    assert client.get(f"/v1/processes/{pid}/versions/{old_snapshot}").json()==snapshot


def test_robot_save_version_ready_to_use(client):
    client.post("/v1/robots",json={"id":"robot","name":"Robot"}).raise_for_status()
    response=client.post("/v1/robots/robot/versions",json={"entrypoint":"python main.py","ready_to_use":True})
    assert response.status_code==201, response.text
    version=response.json()
    assert version["status"]=="published" and version["bundle_sha256"]


def test_team_clone_and_reference_checks_use_saved_configuration(client):
    project, process = setup_project(client)
    client.post("/v1/agents",json={"id":"employee","name":"Employee","role_id":"r","model_id":"m","skill_ids":["s"]}).raise_for_status()
    graph=definition()
    graph["tasks"][0]["agent_id"]="employee"
    save(client,process["id"],graph)
    assert {a["id"] for a in client.get(f"/v1/projects/{project['id']}").json()["team"]}=={"a","employee"}
    assert client.delete("/v1/agents/employee").status_code==409
    response=client.post(f"/v1/projects/{project['id']}/clone",json={"name":"Copy"},headers={"Idempotency-Key":"clone"})
    assert response.status_code==201, response.text
    copied=response.json()
    assert client.get(f"/v1/processes/{copied['processes'][0]['id']}/configuration").json()["definition"]==graph


def test_invalid_run_rolls_back_new_snapshot(client):
    _, process=setup_project(client)
    save(client,process["id"],definition())
    before=client.get(f"/v1/processes/{process['id']}").json()["versions"]
    response=client.post(f"/v1/processes/{process['id']}/runs",json={"input":{"topic_directory":"relative"}},headers={"Idempotency-Key":"invalid"})
    assert response.status_code==422
    assert client.get(f"/v1/processes/{process['id']}").json()["versions"]==before

