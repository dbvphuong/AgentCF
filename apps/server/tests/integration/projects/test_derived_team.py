"""Team is a read-only view of the PM and current saved Process assignments."""

from copy import deepcopy

from test_project_web import client, setup_project, definition


def add_agent(client, id):
    client.post("/v1/agents",json={"id":id,"name":id,"role_id":"r","model_id":"m","skill_ids":["s"]}).raise_for_status()


def ids(client, project):
    return {a["id"] for a in client.get(f"/v1/projects/{project['id']}").json()["team"]}


def test_team_is_pm_plus_saved_nodes_deduplicated_across_processes(client):
    project, first = setup_project(client)
    other, _ = setup_project(client)
    add_agent(client,"employee")
    add_agent(client,"unused")
    second=client.post(f"/v1/projects/{project['id']}/processes",json={"name":"Second"}).json()
    graph=definition()
    for node in graph["tasks"]:
        node["agent_id"]="employee"
    assert ids(client,project)=={"a"}
    # Legacy manually selected membership does not become an authoritative input.
    with client.app.state.database.transaction() as c:
        c.execute("INSERT INTO project_team VALUES (?, 'unused')",(project["id"],))
    for proc in (first,second):
        path=f"/v1/processes/{proc['id']}/versions/{proc['versions'][0]['id']}"
        client.put(path,json={"revision":1,"definition":graph}).raise_for_status()
    team=client.get(f"/v1/projects/{project['id']}").json()["team"]
    assert len(team)==2 and {a["id"] for a in team}=={"a","employee"}
    assert ids(client,other)=={"a"}
    for index,proc in enumerate((first,second)):
        path=f"/v1/processes/{proc['id']}/versions/{proc['versions'][0]['id']}"
        client.put(path,json={"revision":2,"definition":definition()}).raise_for_status()
        assert ids(client,project)==({"a","employee"} if index==0 else {"a"})


def test_any_active_agent_can_publish_without_manual_membership_and_team_uses_latest_version(client):
    project, process=setup_project(client)
    add_agent(client,"employee")
    graph=definition()
    graph["tasks"][0]["agent_id"]="employee"
    path=f"/v1/processes/{process['id']}"
    vid=process["versions"][0]["id"]
    client.put(f"{path}/versions/{vid}",json={"revision":1,"definition":graph}).raise_for_status()
    client.post(f"{path}/versions/{vid}/publish",json={"revision":2}).raise_for_status()
    before=client.get(f"{path}/versions/{vid}").json()
    draft=client.post(path+"/draft").json()["versions"][0]
    assert ids(client,project)=={"a","employee"}
    client.put(f"{path}/versions/{draft['id']}",json={"revision":draft["revision"],"definition":definition()}).raise_for_status()
    assert ids(client,project)=={"a"}
    assert client.get(f"{path}/versions/{vid}").json()==before
    assert client.delete("/v1/agents/employee").status_code==409 # historical Process still references it


def test_change_pm_delete_process_and_clone_recompute_team(client):
    project, process=setup_project(client)
    add_agent(client,"new-pm")
    add_agent(client,"employee")
    graph=definition()
    for task in graph["tasks"]:
        task["agent_id"]="employee"
    path=f"/v1/processes/{process['id']}/versions/{process['versions'][0]['id']}"
    client.put(path,json={"revision":1,"definition":graph}).raise_for_status()
    client.patch(f"/v1/projects/{project['id']}",json={"name":project["name"],"workspace_id":project["workspace_id"],"pm_agent_id":"new-pm"}).raise_for_status()
    assert ids(client,project)=={"new-pm","employee"}
    clone=client.post(f"/v1/projects/{project['id']}/clone",json={"name":"Copy"}).json()
    assert ids(client,clone)=={"new-pm","employee"}
    client.delete(f"/v1/processes/{process['id']}").raise_for_status()
    assert ids(client,project)=={"new-pm"}
    assert ids(client,clone)=={"new-pm","employee"}


def test_manual_team_endpoint_is_deprecated_and_cannot_override_derived_membership(client):
    project,_=setup_project(client)
    add_agent(client,"unused")
    before=deepcopy(client.get(f"/v1/projects/{project['id']}").json())
    response=client.put(f"/v1/projects/{project['id']}/team",json={"agent_ids":["unused"]})
    assert response.status_code==422 and "tự động" in response.json()["detail"]
    assert client.get(f"/v1/projects/{project['id']}").json()==before
