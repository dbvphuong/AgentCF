"""Topic context is validated once, pinned in Run input, and shared without changing cwd."""

import pytest
from test_project_web import client, setup_project, definition


def local_process(client):
    project, process = setup_project(client)
    root = r"E:\Project"
    client.patch(f"/v1/projects/{project['id']}", json={"name":project["name"],"workspace_id":project["workspace_id"],"pm_agent_id":"a","working_directory":root}).raise_for_status()
    code = client.post('/v1/pairing-codes',json={"workspace_id":project['workspace_id'],"name":"PC"}).json()['pairing_code']
    pc = client.post('/v1/runners/pair',json={"pairing_code":code}).json()['runner_id']
    client.post('/v1/skills/s/versions',json={"id":"local","source_path":root+r"\.agents\SKILL.md","source_runner_id":pc}).raise_for_status()
    client.post('/v1/skills/s/versions/local/publish',json={}).raise_for_status()
    vid = process['versions'][0]['id']
    path = f"/v1/processes/{process['id']}/versions/{vid}"
    client.put(path,json={"revision":1,"definition":definition()}).raise_for_status()
    client.post(path+'/publish',json={"revision":2}).raise_for_status()
    return project, process, vid, pc


def test_project_defaults_are_pinned_and_topic_path_is_single_run_input(client):
    project,process,vid,pc=local_process(client)
    ctx=client.get(f'/v1/process-versions/{vid}/run-context').json()
    assert ctx['topic_supported'] and ctx['working_directory']==r'E:\Project' and ctx['runner_id']==pc
    snapshot=client.get(f"/v1/processes/{process['id']}/versions/{vid}").json()
    assert all(t['working_directory']==r'E:\Project' and t['runner_id']==pc for t in snapshot['definition']['tasks'])
    run=client.post('/v1/runs',json={"process_version_id":vid,"input":{"topic_directory":r'E:\Project\Chủ đề 2',"request":"Yêu cầu riêng"}},headers={"Idempotency-Key":"topic"})
    assert run.status_code==202,run.text
    assert run.json()['input']=={"topic_directory":r'E:\Project\Chủ đề 2',"topic":"Chủ đề 2","request":"Yêu cầu riêng"}
    assert len(run.json()['task_runs'])==2
    assert client.get(f"/v1/processes/{process['id']}/versions/{vid}").json()==snapshot
    client.patch(f"/v1/projects/{project['id']}",json={"name":"New","workspace_id":project['workspace_id'],"pm_agent_id":"a","working_directory":r'E:\Other'}).raise_for_status()
    assert client.get(f'/v1/process-versions/{vid}/run-context').json()['working_directory']==r'E:\Project'


@pytest.mark.parametrize('path',['relative',r'E:\Other\Topic',r'E:\Project',r'E:\Project\..\Outside',None,''])
def test_invalid_topic_never_creates_run(client,path):
    _,_,vid,_=local_process(client)
    response=client.post('/v1/runs',json={"process_version_id":vid,"input":{"topic_directory":path}},headers={"Idempotency-Key":"invalid"})
    assert response.status_code==422,response.text
    assert client.get('/v1/runs').json()['total']==0


def test_generic_run_still_accepts_legacy_input_and_context_explains_unsupported(client):
    _,process=setup_project(client)
    vid=process['versions'][0]['id']
    path=f"/v1/processes/{process['id']}/versions/{vid}"
    client.put(path,json={"revision":1,"definition":definition()}).raise_for_status()
    client.post(path+'/publish',json={"revision":2}).raise_for_status()
    assert client.get(f'/v1/process-versions/{vid}/run-context').json()['topic_supported'] is False
    assert client.post('/v1/runs',json={"process_version_id":vid,"input":{"arbitrary":123}},headers={"Idempotency-Key":"legacy"}).status_code==202


def test_removed_source_pc_reports_reconfiguration_instead_of_generic_path_error(client):
    _,process,_,pc=local_process(client)
    client.delete(f'/v1/runners/{pc}').raise_for_status()
    draft=client.post(f"/v1/processes/{process['id']}/draft").json()['versions'][0]
    response=client.post(f"/v1/processes/{process['id']}/versions/{draft['id']}/publish",json={"revision":draft['revision']})
    assert response.status_code==422
    assert 'Sửa Skill' in response.json()['detail']
