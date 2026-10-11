import socket
import urllib.request

import numpy as np
import pytest


def test_ai_has_majority_weight_and_invalid_scores_fail():
    from services.scoring import ai_final_score
    assert ai_final_score(90, 50) == pytest.approx(78)
    assert ai_final_score(20, 100) == pytest.approx(44)
    with pytest.raises(ValueError):
        ai_final_score(float('nan'), 80)


def test_visual_diversity_prefers_new_content():
    from services.scoring import select_segments
    segments = [
        dict(filename='a.mp4', start=0., end=5., score=90, selected=False, visualEmbedding=[1., 0.]),
        dict(filename='a.mp4', start=10., end=15., score=89, selected=False, visualEmbedding=[1., 0.]),
        dict(filename='a.mp4', start=20., end=25., score=87, selected=False, visualEmbedding=[0., 1.]),
    ]
    assert [s['start'] for s in select_segments(segments, 10, ['a.mp4'])] == [0, 20]


def test_missing_ai_model_has_clear_error(tmp_path):
    from services.ai_scorer import LocalAestheticScorer
    with pytest.raises(ValueError, match='setup_ai.py'):
        LocalAestheticScorer(tmp_path)


def test_clip_preprocessing_preserves_rgb_and_shape():
    from services.ai_scorer import preprocess_frame
    frame = np.zeros((90, 160, 3), dtype=np.uint8)
    frame[:, :, 2] = 255  # OpenCV red is BGR channel 2.
    tensor = preprocess_frame(frame)
    assert tensor.shape == (3, 224, 224)
    assert tensor.dtype == np.float32
    assert float(tensor[0, 0, 0]) == pytest.approx((1 - .48145466) / .26862954, abs=1e-5)
    assert float(tensor[2, 0, 0]) == pytest.approx(-.40821073 / .27577711, abs=1e-5)


def test_local_inference_runs_without_network(monkeypatch):
    from services.ai_scorer import LocalAestheticScorer
    import config

    def forbidden(*args, **kwargs):
        raise AssertionError('A inferência local não pode usar a rede.')

    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    scorer = LocalAestheticScorer(config.AI_MODELS_DIR)
    dark = np.zeros((90, 160, 3), dtype=np.uint8)
    detail = np.random.default_rng(23).integers(0, 255, (90, 160, 3), dtype=np.uint8)
    result = scorer.score_frames([dark, detail])
    assert 0 <= result['aiScore'] <= 100
    assert len(result['aiFrameScores']) == 2
    assert abs(result['aiFrameScores'][0] - result['aiFrameScores'][1]) > .01
    assert len(result['visualEmbedding']) == 512
    assert np.linalg.norm(result['visualEmbedding']) == pytest.approx(1, abs=1e-5)
    assert result['aiModel'] == 'CLIP ViT-B/32 + LAION Aesthetic V1 (ONNX int8)'


def test_corrupt_model_is_rejected_before_inference(tmp_path):
    from services.ai_scorer import LocalAestheticScorer, VISION_FILENAME, HEAD_FILENAME
    (tmp_path / VISION_FILENAME).write_bytes(b'corrupted')
    (tmp_path / HEAD_FILENAME).write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='setup_ai.py'):
        LocalAestheticScorer(tmp_path)
