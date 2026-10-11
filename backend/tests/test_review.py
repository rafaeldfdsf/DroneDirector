import json
import time
import cv2
import numpy as np
import pytest
from test_pipeline import client


def test_normalize_order_trim_and_short_duration():
    from services.review import normalize_selection
    candidates = [dict(id='a', filename='a.mp4', start=0., end=8.), dict(id='b', filename='a.mp4', start=8., end=16.)]
    result = normalize_selection(candidates, ['b', 'a'], 15)
    assert [s['id'] for s in result] == ['b', 'a']
    assert result[-1]['end'] == 7
    assert sum(s['end']-s['start'] for s in result) == 15
    assert normalize_selection(candidates, ['a'], 30)[0]['end'] == 8


def test_review_rejects_empty_unknown_duplicate_and_overlap():
    from services.review import normalize_selection
    candidates = [dict(id='a', filename='a.mp4', start=0., end=5.), dict(id='b', filename='a.mp4', start=4., end=8.)]
    for ids in [[], ['z'], ['a','a'], ['a','b']]:
        with pytest.raises(ValueError):
            normalize_selection(candidates, ids, 30)


def test_analysis_stops_at_review_without_export(client, tmp_path):
    path = tmp_path/'tiny.mp4'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (96,64))
    for i in range(23):
        frame=np.full((64,96,3),120,np.uint8)
        cv2.rectangle(frame,(i,10),(i+20,40),(30,80,150),-1)
        writer.write(frame)
    writer.release()
    pid=client.post('/api/projects').json()['projectId']
    assert client.post(f'/api/projects/{pid}/videos',files={'videos':('tiny.mp4',path.read_bytes())}).status_code==200
    assert client.post(f'/api/projects/{pid}/analyze',json={'duration':15}).status_code==202
    until=time.monotonic()+60
    while time.monotonic()<until:
        status=client.get(f'/api/projects/{pid}/status').json()
        if status['status'] in ['review','failed']:
            break
        time.sleep(.1)
    assert status['status']=='review',status
    assert client.get(f'/api/projects/{pid}/result').status_code==409
    review=client.get(f'/api/projects/{pid}/review').json()
    assert review['candidates'] and review['selectedIds']
    assert 'visualEmbedding' not in review['candidates'][0]
    cid=review['selectedIds'][0]
    assert client.get(f'/api/projects/{pid}/thumbnail/{cid}').status_code==200
    preview=client.get(f'/api/projects/{pid}/preview/{cid}',headers={'Range':'bytes=0-99'})
    assert preview.status_code==206 and len(preview.content)==100
    assert client.get(f'/api/projects/{pid}/preview/unknown').status_code==404
    suggestion=client.post(f'/api/projects/{pid}/suggest',json={'prompt':''})
    assert suggestion.status_code==200
    assert client.post(f'/api/projects/{pid}/export',json={'selectedIds':[],'duration':15}).status_code==400
    assert client.post(f'/api/projects/{pid}/export',json={'selectedIds':[cid],'duration':15}).status_code==202
    until=time.monotonic()+60
    while time.monotonic()<until:
        status=client.get(f'/api/projects/{pid}/status').json()
        if status['status'] in ['completed','review','failed']:
            break
        time.sleep(.1)
    assert status['status']=='completed',status
    assert abs(status['duration']-2.3)<.1
    assert client.get(f'/api/projects/{pid}/result').status_code==200


def prepared_project(client):
    from models.project import store
    from services.review import save_review
    pid=client.post('/api/projects').json()['projectId']
    project=store[pid]
    project.files=['a.mp4']
    project.status='review'
    candidates=[dict(id='a',filename='a.mp4',start=0.,end=5.,score=70.,aiScore=70.,visualEmbedding=[1.,0.]),
                dict(id='b',filename='a.mp4',start=5.,end=10.,score=70.,aiScore=70.,visualEmbedding=[0.,1.])]
    save_review(project,dict(candidates=candidates,selectedIds=['a'],suggestedIds=['a'],duration=15,enhanceColors=True,prompt='',warnings=[]))
    return project


def test_concurrent_export_rejected(client,monkeypatch):
    from services.processor import executor
    project=prepared_project(client)
    submitted=[]
    monkeypatch.setattr(executor,'submit',lambda *args:submitted.append(args))
    url=f'/api/projects/{project.project_id}/export'
    assert client.post(url,json={'selectedIds':['a'],'duration':15}).status_code==202
    assert client.post(url,json={'selectedIds':['a'],'duration':15}).status_code==409
    assert len(submitted)==1


def test_failed_reexport_preserves_result(client,monkeypatch):
    from services import processor
    from models.project import ProcessRequest
    project=prepared_project(client)
    final=project.directory/'output'/'final.mp4'
    final.write_bytes(b'previous valid result')
    def fail(*args):
        raise RuntimeError('Simulated render failure')
    monkeypatch.setattr(processor,'extract_clip',fail)
    processor.export_project(project,['b'],ProcessRequest(duration=15))
    assert project.status=='review'
    assert project.error=='Simulated render failure'
    assert final.read_bytes()==b'previous valid result'
    assert client.get(f'/api/projects/{project.project_id}/result').content==b'previous valid result'
    from services.review import load_review
    assert load_review(project)['selectedIds']==['b']


def test_metadata_failure_preserves_previous_video(client,monkeypatch):
    from pathlib import Path
    from services import processor
    from models.project import ProcessRequest
    project=prepared_project(client)
    final=project.directory/'output'/'final.mp4'
    final.write_bytes(b'previous valid result')
    monkeypatch.setattr(processor,'extract_clip',lambda *args:None)
    def render(clips,path):
        path.write_bytes(b'new render')
        return 5.
    monkeypatch.setattr(processor,'concatenate',render)
    original=Path.write_text
    def fail_metadata(path,*args,**kwargs):
        if path.name.startswith('export'):
            raise OSError('Metadata unavailable')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail_metadata)
    processor.export_project(project,['a'],ProcessRequest(duration=15))
    assert project.status=='review'
    assert final.read_bytes()==b'previous valid result'


def test_backup_cleanup_does_not_fail_successful_export(client,monkeypatch):
    from pathlib import Path
    from services import processor
    from models.project import ProcessRequest
    project=prepared_project(client)
    final=project.directory/'output'/'final.mp4'
    final.write_bytes(b'previous valid result')
    monkeypatch.setattr(processor,'extract_clip',lambda *args:None)
    def render(clips,path):
        path.write_bytes(b'new valid render')
        return 5.
    monkeypatch.setattr(processor,'concatenate',render)
    original=Path.unlink
    def fail_cleanup(path,*args,**kwargs):
        if path.name=='previous.mp4':
            raise OSError('Backup in use')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'unlink',fail_cleanup)
    processor.export_project(project,['a'],ProcessRequest(duration=15))
    assert project.status=='completed'
    assert final.read_bytes()==b'new valid render'


def test_suggest_reuses_embeddings(client,monkeypatch):
    from services import prompt_scorer,analyzer
    project=prepared_project(client)
    class Scorer:
        def encode(self,text):
            return np.array([0.,1.])
    monkeypatch.setattr(prompt_scorer,'get_prompt_scorer',lambda:Scorer())
    def forbidden(*args):
        raise AssertionError('Unexpected video analysis')
    monkeypatch.setattr(analyzer,'analyze_video',forbidden)
    result=client.post(f'/api/projects/{project.project_id}/suggest',json={'prompt':'Uma imagem azul'})
    assert result.status_code==200
    data=result.json()
    assert data['prompt']=='Uma imagem azul'
    assert data['candidates'][1]['promptAdjustment']>data['candidates'][0]['promptAdjustment']
    assert 'visualEmbedding' not in data['effectiveSegments'][0]
