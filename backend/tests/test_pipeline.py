import json
import shutil
import subprocess
import time

import pytest
from fastapi.testclient import TestClient


def test_weighted_score():
    from services.scoring import final_score
    assert final_score(80, 90, 70, 60) == pytest.approx(79)


def test_selection_diversity_and_chronology():
    from services.scoring import select_segments
    segments = [dict(filename=f, start=i * 5, end=i * 5 + 5, score=99 - i, selected=False)
                for f in ['a.mp4', 'b.mp4'] for i in range(6)]
    chosen = select_segments(segments, 15, ['a.mp4', 'b.mp4'])
    assert len(chosen) == 3
    assert {s['filename'] for s in chosen} == {'a.mp4', 'b.mp4'}
    for a in chosen:
        for b in chosen:
            if a is not b and a['filename'] == b['filename']:
                assert a['end'] <= b['start'] or b['end'] <= a['start']
    assert chosen == sorted(chosen, key=lambda s: (s['filename'], s['start']))


def test_short_material_and_fallback():
    from services.scoring import select_segments
    short = [dict(filename='a.mp4', start=0., end=2.3, score=70, selected=False)]
    assert select_segments(short, 30, ['a.mp4'])[0]['end'] == 2.3
    consecutive = [dict(filename='a.mp4', start=i * 5, end=i * 5 + 5, score=90 - i, selected=False)
                   for i in range(3)]
    assert len(select_segments(consecutive, 15, ['a.mp4'])) == 3


@pytest.fixture
def client(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, 'PROJECTS_DIR', tmp_path / 'projects')
    from main import app
    from models.project import store
    store.clear()
    with TestClient(app) as api:
        yield api


def test_api_validation(client):
    assert client.get('/api/projects/not-a-uuid/status').status_code == 404
    pid = client.post('/api/projects').json()['projectId']
    assert client.post(f'/api/projects/{pid}/process', json={'duration': 30}).status_code == 400
    assert client.post(f'/api/projects/{pid}/videos', files={'videos': ('bad.exe', b'bad')}).status_code == 400
    assert client.post(f'/api/projects/{pid}/videos', files={'videos': ('empty.mp4', b'')}).status_code == 400
    assert client.post(f'/api/projects/{pid}/videos', files={'videos': ('broken.mp4', b'broken')}).status_code == 400
    invalid = client.post(f'/api/projects/{pid}/process', json={'duration': 20})
    assert invalid.status_code == 422
    assert isinstance(invalid.json()['detail'], str)
    assert client.get(f'/api/projects/{pid}/result').status_code == 409


def test_missing_ffmpeg_returns_actionable_error(client, tmp_path, monkeypatch):
    import cv2
    import numpy as np
    import config
    path = tmp_path / 'tiny.mp4'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64, 64))
    writer.write(np.full((64, 64, 3), 120, dtype=np.uint8))
    writer.release()
    pid = client.post('/api/projects').json()['projectId']
    assert client.post(f'/api/projects/{pid}/videos', files={'videos': ('tiny.mp4', path.read_bytes())}).status_code == 200
    monkeypatch.setattr(config, 'FFMPEG', 'not-an-installed-drone-ffmpeg')
    response = client.post(f'/api/projects/{pid}/process', json={'duration': 30})
    assert response.status_code == 503
    assert 'README' in response.json()['detail']


def test_reserved_windows_names_and_upload_rollback(client, tmp_path):
    import cv2
    import numpy as np
    path = tmp_path / 'tiny.mp4'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64, 64))
    writer.write(np.full((64, 64, 3), 120, dtype=np.uint8))
    writer.release()
    pid = client.post('/api/projects').json()['projectId']
    response = client.post(f'/api/projects/{pid}/videos', files={'videos': ('CON.mp4', path.read_bytes())})
    assert response.status_code == 200
    assert response.json()['videos'] == ['video_CON.mp4']
    failed = client.post(f'/api/projects/{pid}/videos', files=[('videos', ('new.mp4', path.read_bytes())), ('videos', ('bad.mov', b'bad'))])
    assert failed.status_code == 400
    assert len(list((tmp_path / 'projects' / pid / 'original').iterdir())) == 1
    assert client.get(f'/api/projects/{pid}/status').json()['status'] == 'ready'


@pytest.mark.parametrize('duration,count', [(15, 3), (30, 6), (60, 12)])
def test_requested_durations(duration, count):
    from services.scoring import select_segments
    segments = [dict(filename='a.mp4', start=i * 5, end=i * 5 + 5, score=90 - i, selected=False)
                for i in range(25)]
    chosen = select_segments(segments, duration, ['a.mp4'])
    assert len(chosen) == count
    assert sum(s['end'] - s['start'] for s in chosen) == duration


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg/ffprobe necessários')
@pytest.mark.parametrize('enhance', [True, False])
def test_synthetic_end_to_end(client, tmp_path, enhance):
    sources = []
    for i, (size, fps, duration) in enumerate([('320x180', 24, 3), ('180x320', 30, 2)]):
        path = tmp_path / f'synthetic_{i}.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        f'testsrc2=size={size}:rate={fps}', '-t', str(duration),
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True)
        sources.append(path)
    pid = client.post('/api/projects').json()['projectId']
    files = [('videos', ('same.mp4', p.read_bytes(), 'video/mp4')) for p in sources]
    assert client.post(f'/api/projects/{pid}/videos', files=files).status_code == 200
    started = time.monotonic()
    response = client.post(f'/api/projects/{pid}/process', json={'duration': 15, 'enhanceColors': enhance})
    assert response.status_code == 202
    assert time.monotonic() - started < 2
    assert client.post(f'/api/projects/{pid}/process', json={'duration': 15}).status_code == 409
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        status = client.get(f'/api/projects/{pid}/status').json()
        if status['status'] in ('completed', 'failed'):
            break
        time.sleep(.2)
    assert status['status'] == 'completed', status
    assert status['progress'] == 100
    assert status['selectedMoments'] == 2
    assert status['duration'] == pytest.approx(5, abs=.15)
    result = client.get(f'/api/projects/{pid}/result')
    assert result.headers['content-type'] == 'video/mp4'
    assert len(result.content) > 1000
    partial = client.get(f'/api/projects/{pid}/result', headers={'Range': 'bytes=0-99'})
    assert partial.status_code == 206
    assert len(partial.content) == 100
    analysis = json.loads((tmp_path / 'projects' / pid / 'data' / 'analysis.json').read_text())
    assert len(analysis['videos']) == 2
    for video in analysis['videos']:
        assert video['segments'][0]['selected']
        for name in ['sharpness', 'exposure', 'stability', 'movement', 'score', 'aiScore', 'technicalScore']:
            assert 0 <= video['segments'][0][name] <= 100
        assert len(video['segments'][0]['aiFrameScores']) == 3
        assert 'visualEmbedding' not in video['segments'][0]
    assert analysis['selectionMethod'] == 'local-ai'
    assert analysis['scoreWeights'] == {'ai': .7, 'technical': .3}
    assert status['selectionMethod'] == 'local-ai'
    assert 'LAION' in status['aiModel']
    output = tmp_path / 'projects' / pid / 'output' / 'final.mp4'
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)], capture_output=True, text=True, check=True)
    streams = json.loads(probe.stdout)['streams']
    assert len(streams) == 1
    assert streams[0]['codec_name'] == 'h264'
    assert streams[0]['pix_fmt'] == 'yuv420p'
    assert (streams[0]['width'], streams[0]['height']) == (1920, 1080)


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg/ffprobe necessários')
@pytest.mark.parametrize('duration,moments', [(30, 6), (60, 12)])
def test_full_length_export(client, tmp_path, duration, moments):
    path = tmp_path / 'long_synthetic.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=24',
                    '-t', '65', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True)
    pid = client.post('/api/projects').json()['projectId']
    assert client.post(f'/api/projects/{pid}/videos', files={'videos': ('synthetic.mp4', path.read_bytes())}).status_code == 200
    assert client.post(f'/api/projects/{pid}/process', json={'duration': duration, 'enhanceColors': True}).status_code == 202
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        status = client.get(f'/api/projects/{pid}/status').json()
        if status['status'] in ('completed', 'failed'):
            break
        time.sleep(.2)
    assert status['status'] == 'completed', status
    assert status['duration'] == pytest.approx(duration, abs=.15)
    assert duration / 8 <= status['selectedMoments'] <= duration / 3 + 1


def test_missing_ai_model_blocks_processing_instead_of_fallback(client, tmp_path, monkeypatch):
    import config
    import cv2
    import numpy as np
    path = tmp_path / 'tiny.mp4'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64, 64))
    writer.write(np.full((64, 64, 3), 120, dtype=np.uint8))
    writer.release()
    pid = client.post('/api/projects').json()['projectId']
    assert client.post(f'/api/projects/{pid}/videos', files={'videos': ('tiny.mp4', path.read_bytes())}).status_code == 200
    monkeypatch.setattr(config, 'AI_MODELS_DIR', tmp_path / 'missing-ai-models')
    response = client.post(f'/api/projects/{pid}/process', json={'duration': 30})
    assert response.status_code == 503
    assert 'setup_ai.py' in response.json()['detail']
    assert client.get('/api/ai/status').json()['ready'] is False
    assert client.get(f'/api/projects/{pid}/status').json()['status'] == 'ready'
