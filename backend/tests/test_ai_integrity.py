import pytest


def test_readiness_rejects_corrupt_head_even_with_valid_vision(tmp_path):
    import config
    from services.ai_scorer import HEAD_FILENAME, VISION_FILENAME, check_model_files
    # Link to the real large model; this test changes only a tiny head file.
    (tmp_path / VISION_FILENAME).hardlink_to(config.AI_MODELS_DIR / VISION_FILENAME)
    (tmp_path / HEAD_FILENAME).write_bytes(b'bad')
    with pytest.raises(ValueError, match='setup_ai.py'):
        check_model_files(tmp_path)
