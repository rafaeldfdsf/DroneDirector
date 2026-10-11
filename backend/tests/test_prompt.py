import numpy as np
import pytest


def test_prompt_empty_uses_base_score():
    from services.prompt_scorer import apply_prompt
    segments = [dict(score=70., visualEmbedding=[1., 0.], promptAdjustment=5.)]
    apply_prompt(segments, '   ')
    assert segments[0]['score'] == 70.
    assert segments[0]['promptAdjustment'] == 0.


def test_prompt_adjustment_bounded():
    from services.prompt_scorer import apply_prompt
    class Scorer:
        def encode(self, text):
            return np.array([1., 0.])
    segments = [dict(score=70., visualEmbedding=[1.,0.]), dict(score=70., visualEmbedding=[-1.,0.])]
    apply_prompt(segments, 'rio', Scorer())
    assert [s['promptAdjustment'] for s in segments] == [10., -10.]


def test_missing_or_corrupt_prompt_model(tmp_path):
    from services.prompt_scorer import check_prompt_model_files
    with pytest.raises(ValueError, match='texto'):
        check_prompt_model_files(tmp_path)


def test_prompt_lengths_and_whitespace():
    from services.prompt_scorer import apply_prompt
    with pytest.raises(ValueError):
        apply_prompt([], 'a'*501)


def test_portuguese_image_text_matching_offline(monkeypatch):
    import socket
    import urllib.request
    from services.prompt_scorer import get_prompt_scorer
    from services.ai_scorer import get_ai_scorer
    def forbidden(*args, **kwargs):
        raise AssertionError('Network access during inference')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    text = get_prompt_scorer()
    vision = get_ai_scorer()
    images=[np.full((224,224,3),(0,0,255),np.uint8),np.full((224,224,3),(255,0,0),np.uint8)]
    features=np.array([vision.score_frames([image])['visualEmbedding'] for image in images])
    for expected, prompt in enumerate(['Uma imagem vermelha','Uma imagem azul']):
        vector=text.encode(prompt)
        assert vector.shape==(512,)
        assert np.linalg.norm(vector)==pytest.approx(1.,abs=1e-5)
        assert int(np.argmax(features@vector))==expected
