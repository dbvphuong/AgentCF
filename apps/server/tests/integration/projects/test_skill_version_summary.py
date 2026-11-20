"""Skill catalog distinguishes an available published version from draft-only metadata."""

from test_project_web import client


def summary(client):
    detail=client.get('/v1/skills/summary').json()
    row=next(s for s in client.get('/v1/skills').json() if s['id']=='summary')
    fields=('published_version_number','latest_version_number','latest_version_status')
    assert {k:detail[k] for k in fields}=={k:row[k] for k in fields}
    return tuple(detail[k] for k in fields)


def test_catalog_summary_tracks_none_draft_published_and_newer_draft(client):
    client.post('/v1/skills',json={'id':'summary','name':'Summary','is_global':True}).raise_for_status()
    assert summary(client)==(None,None,None)
    client.post('/v1/skills/summary/versions',json={'id':'summary-1','instructions':'First'}).raise_for_status()
    assert summary(client)==(None,1,'draft')
    client.post('/v1/skills/summary/versions/summary-1/publish',json={}).raise_for_status()
    assert summary(client)==(1,1,'published')
    first=client.get('/v1/skills/summary/versions/summary-1').json()
    client.post('/v1/skills/summary/versions',json={'id':'summary-2','instructions':'Second'}).raise_for_status()
    assert summary(client)==(1,2,'draft')
    assert client.get('/v1/skills/summary/versions/summary-1').json()==first
    client.delete('/v1/skills/summary/versions/summary-2').raise_for_status()
    assert summary(client)==(1,1,'published')
    client.post('/v1/skills/summary/versions',json={'id':'summary-next','instructions':'Second'}).raise_for_status()
    client.post('/v1/skills/summary/versions/summary-next/publish',json={}).raise_for_status()
    assert summary(client)==(2,2,'published')
