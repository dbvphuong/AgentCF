"""Reasoning level belongs to the node and is frozen in its Run snapshot."""
import pytest

from test_project_web import client, definition, setup_project
from test_current_configuration import save, run


def test_saved_level_is_frozen_per_run_and_per_node(client):
    _,process=setup_project(client)
    graph=definition()
    graph["tasks"][0]["runtime"]["reasoning_effort"]="high"
    save(client,process["id"],graph)
    first=run(client,process["id"],"high")
    path=f"/v1/processes/{process['id']}/versions/{first['process_version_id']}"
    snapshot=client.get(path).json()
    assert snapshot["definition"]["tasks"][0]["runtime"]["reasoning_effort"]=="high"
    assert "reasoning_effort" not in snapshot["definition"]["tasks"][1]["runtime"]
    graph["tasks"][0]["runtime"]["reasoning_effort"]="medium"
    save(client,process["id"],graph)
    second=run(client,process["id"],"medium")
    newer=client.get(f"/v1/processes/{process['id']}/versions/{second['process_version_id']}").json()
    assert newer["definition"]["tasks"][0]["runtime"]["reasoning_effort"]=="medium"
    assert client.get(path).json()==snapshot


@pytest.mark.parametrize("adapter,level",[("codex","invalid"),("codex",[]),("antigravity","max")])
def test_invalid_tool_level_cannot_be_saved(client,adapter,level):
    _,process=setup_project(client)
    graph=definition()
    graph["tasks"][0]["runtime"].update(adapter=adapter,reasoning_effort=level)
    config=client.get(f"/v1/processes/{process['id']}/configuration").json()
    response=client.put(f"/v1/processes/{process['id']}/configuration",json={"definition":graph,"expected_token":config["configuration_token"]})
    assert response.status_code==422 and "Mức suy luận" in response.json()["detail"]
