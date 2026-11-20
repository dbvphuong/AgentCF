from test_runner_actions import env
from agent_cf_server.infrastructure.projects.repository import ProjectRepository
from agent_cf_server.infrastructure.processes.repository import ProcessRepository
from agent_cf_server.infrastructure.runs.repository import RunRepository

DEVICE='device-'+'a'*64
KEY='b'*64


def code(client,target=None):
    response=client.post('/v1/pairing-codes',json={'workspace_id':'ws','name':'Same name','target_runner_id':target})
    assert response.status_code==201,response.text
    return response.json()['pairing_code']


def pair(client,target=None,device=DEVICE,key=KEY):
    response=client.post('/v1/runners/pair',json={'pairing_code':code(client,target),'device_id':device,'device_key':key,'machine_fingerprint':'hostname'})
    assert response.status_code==201,response.text
    return response.json()


def test_same_device_reuses_identity_and_rotates_credential_without_losing_name(env):
    client,db=env
    first=pair(client)
    rid=first['runner_id']
    auth={'Authorization':'Bearer '+first['runner_token']}
    client.patch('/v1/runners/'+rid,json={'name':'Friendly name'}).raise_for_status()
    client.post('/v1/runners/'+rid+'/sessions',json={'client_version':'test'},headers=auth).raise_for_status()
    assert client.get('/v1/runners/'+rid).json()['machine_fingerprint']=='hostname'
    second=pair(client)
    assert second['runner_id']==rid
    assert second['runner']['name']=='Friendly name'
    assert len(client.get('/v1/runners').json())==1
    assert 'device_key_hash' not in second['runner']
    assert 'device_key' not in second['runner']
    assert client.post('/v1/runners/'+rid+'/sessions',json={'client_version':'test'},headers=auth).status_code==401


def test_targeted_connect_binds_legacy_pc_and_disconnect_keeps_identity(env):
    client,db=env
    legacy=client.post('/v1/runners/pair',json={'pairing_code':code(client)}).json()
    rid=legacy['runner_id']
    bound=pair(client,rid)
    assert bound['runner_id']==rid and len(client.get('/v1/runners').json())==1
    auth={'Authorization':'Bearer '+bound['runner_token']}
    client.post('/v1/runners/'+rid+'/sessions',json={'client_version':'test'},headers=auth).raise_for_status()
    assert client.post('/v1/runners/'+rid+'/disconnect').status_code==204
    assert client.get('/v1/runners/'+rid).json()['display_status']=='offline'
    assert client.post('/v1/runners/'+rid+'/sessions',json={'client_version':'test'},headers=auth).status_code==401
    assert pair(client,rid)['runner_id']==rid


def test_device_proof_required_for_untargeted_reconnect_and_different_devices_not_merged_by_name(env):
    client,db=env
    first=pair(client)
    response=client.post('/v1/runners/pair',json={'pairing_code':code(client),'device_id':DEVICE,'device_key':'c'*64})
    assert response.status_code==409
    second=pair(client,device='device-'+'d'*64)
    assert second['runner_id']!=first['runner_id']
    assert len(client.get('/v1/runners').json())==2
    response=client.post('/v1/runners/pair',json={'pairing_code':code(client,first['runner_id']),'device_id':'device-'+'d'*64,'device_key':KEY})
    assert response.status_code==409


def test_disconnect_and_repair_reject_unfinished_run(env):
    client,db=env
    first=pair(client)
    pc=first['runner_id']
    ProjectRepository(db).create_project(project_id='p',workspace_id='ws',name='Project')
    ProcessRepository(db).create_process(process_id='proc',project_id='p',name='Process')
    ProcessRepository(db).store_published(workspace_id='ws',project_id='p',process_id='proc',version_id='v',version_number=1,definition={'definition_format_version':'1','interpreter_version':'dag-v1','tasks':[{'id':'node','task_key':'node','runner_id':pc}],'dependencies':[]},snapshot_sha256='a'*64)
    run=RunRepository(db).create_from_version(version_id='v',principal_id='operator',request_key='run',request_sha256='b'*64)
    # When a run is merely queued, disconnecting is rejected but reconnecting is allowed to pick up work
    assert client.post('/v1/runners/'+pc+'/disconnect').status_code==409
    assert client.post('/v1/runners/pair',json={'pairing_code':code(client,pc),'device_id':DEVICE,'device_key':KEY}).status_code==201

    # But when an attempt is actively executing, reconnect is rejected
    repaired=pair(client,pc)
    auth_re={'Authorization':'Bearer '+repaired['runner_token']}
    sid=client.post('/v1/runners/'+pc+'/sessions',json={'client_version':'test'},headers=auth_re).json()['id']
    task_run_id=client.get('/v1/runs/'+run['run_id']).json()['task_runs'][0]['id']
    client.post('/v1/task-runs/'+task_run_id+'/claim',json={'session_id':sid,'lease_seconds':60},headers={**auth_re,'Idempotency-Key':'claim-1'}).raise_for_status()
    assert client.post('/v1/runners/pair',json={'pairing_code':code(client,pc),'device_id':DEVICE,'device_key':KEY}).status_code==409


def test_memory_telemetry_roundtrip_and_invalid_values(env):
    client,db=env
    paired=pair(client);rid=paired['runner_id'];auth={'Authorization':'Bearer '+paired['runner_token']}
    sid=client.post('/v1/runners/'+rid+'/sessions',json={'client_version':'test'},headers=auth).json()['id']
    payload={'session_id':sid,'cpu_percent':23.4,'ram_percent':50,'memory_total_bytes':16*1024**3,'memory_used_bytes':8*1024**3}
    assert client.post('/v1/runners/'+rid+'/heartbeat',json=payload,headers=auth).status_code==200
    pc=client.get('/v1/runners/'+rid).json()
    assert pc['cpu_percent']==23.4 and pc['memory_used_bytes']==8*1024**3 and pc['memory_total_bytes']==16*1024**3
    assert client.post('/v1/runners/'+rid+'/heartbeat',json={**payload,'memory_used_bytes':32*1024**3},headers=auth).status_code==422


def test_authenticated_legacy_client_upgrade_binds_existing_pc_without_pairing_again(env):
    client,db=env
    first=client.post('/v1/runners/pair',json={'pairing_code':code(client)}).json()
    rid=first['runner_id'];auth={'Authorization':'Bearer '+first['runner_token']}
    response=client.post('/v1/runners/'+rid+'/sessions',json={'client_version':'0.3.0','device_id':DEVICE,'device_key':KEY},headers=auth)
    assert response.status_code==201,response.text
    assert pair(client)['runner_id']==rid
    assert len(client.get('/v1/runners').json())==1
