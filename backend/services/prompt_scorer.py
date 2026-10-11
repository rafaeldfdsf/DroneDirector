"""Portuguese text-to-image relevance, entirely local after explicit setup."""
from functools import lru_cache
from pathlib import Path
import numpy as np
import onnxruntime as ort
from safetensors.numpy import load_file
from tokenizers import Tokenizer
import config
from services.ai_scorer import _cached_digest

PROMPT_REVISION = '58edf8cada9e398793dca955574a48cbb7f18be2'
PROMPT_MODEL = 'sentence-transformers/clip-ViT-B-32-multilingual-v1'
PROMPT_FILES = {
    'onnx/model_quint8_avx2.onnx': 'fbc8fbeaa5237d96bd1bf430057c70d34de8334a463e933a5faa305f6caeed9c',
    'tokenizer.json': '5b4e1a8171c81dfd666ae40265b9530c6e0b3d53923fe8ac493dcc84229adf81',
    '2_Dense/model.safetensors': 'd12568dc7300970a4d3dbb49068ad16cd89b99840b74b026f8e48071e9414f74',
    '1_Pooling/config.json': 'a37f83ada23e7887be6b88f4998927dbeac0038af301553c7cd5461413bf1a56',
    '2_Dense/config.json': '48f4dfaf605a6c2869cd200970e54911c6c15053781d2bdcf3e81e89e77662ed',
}
PROMPT_ERROR = 'O modelo de texto da IA local está ausente ou corrompido. Executa .\\.venv\\Scripts\\python.exe setup_ai.py no backend, ou deixa o prompt vazio.'


def prompt_directory() -> Path:
    return config.AI_MODELS_DIR / 'prompt'


def check_prompt_model_files(directory: Path | None = None) -> None:
    directory = directory if directory is not None else prompt_directory()
    for name, digest in PROMPT_FILES.items():
        path = directory / name
        if not path.is_file():
            raise ValueError(PROMPT_ERROR)
        stat = path.stat()
        if _cached_digest(str(path.resolve()), stat.st_size, stat.st_mtime_ns) != digest:
            raise ValueError(PROMPT_ERROR)


class LocalPromptScorer:
    def __init__(self, directory: Path):
        check_prompt_model_files(directory)
        self.tokenizer = Tokenizer.from_file(str(directory / 'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=128)
        weights = load_file(str(directory / '2_Dense/model.safetensors'))
        self.projection = weights['linear.weight']
        if self.projection.shape != (512, 768):
            raise ValueError(PROMPT_ERROR)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        ort.disable_telemetry_events()
        self.session = ort.InferenceSession(str(directory / 'onnx/model_quint8_avx2.onnx'),
                                           sess_options=options, providers=['CPUExecutionProvider'])

    def encode(self, prompt: str) -> np.ndarray:
        tokens = self.tokenizer.encode(prompt)
        ids = np.array([tokens.ids], dtype=np.int64)
        mask = np.array([tokens.attention_mask], dtype=np.int64)
        hidden = self.session.run(None, {'input_ids': ids, 'attention_mask': mask})[0]
        if hidden.shape != (1, ids.shape[1], 768):
            raise ValueError('O modelo de texto devolveu dados inválidos.')
        pooled = (hidden * mask[...,None]).sum(axis=1) / max(1, mask.sum())
        vector = (pooled @ self.projection.T)[0].astype(np.float32)
        norm = float(np.linalg.norm(vector))
        if not np.isfinite(vector).all() or norm < 1e-8:
            raise ValueError('Não foi possível compreender o prompt com IA local.')
        return vector / norm


@lru_cache(maxsize=1)
def _load_scorer(directory: str) -> LocalPromptScorer:
    return LocalPromptScorer(Path(directory))


def get_prompt_scorer() -> LocalPromptScorer:
    check_prompt_model_files()
    return _load_scorer(str(prompt_directory().resolve()))


def apply_prompt(segments: list[dict], prompt: str, scorer=None) -> dict:
    if len(prompt) > 500:
        raise ValueError('O prompt pode ter no máximo 500 caracteres.')
    for segment in segments:
        segment['promptAdjustment'] = 0.
        segment['promptSimilarity'] = None
    if not prompt.strip():
        return {'prompt': '', 'warnings': []}
    vector = (scorer if scorer is not None else get_prompt_scorer()).encode(prompt.strip())
    similarities = [float(np.dot(vector, np.array(s['visualEmbedding']))) for s in segments]
    center = float(np.mean(similarities)) if similarities else 0.
    for segment, similarity in zip(segments, similarities):
        segment['promptSimilarity'] = round(similarity, 6)
        segment['promptAdjustment'] = round(float(np.clip((similarity-center)*50, -10, 10)), 6)
    warnings = []
    if not similarities or max(similarities)-min(similarities) < .02:
        warnings.append('O prompt distingue pouco estes momentos. A qualidade visual continua a orientar a seleção.')
    return {'prompt': prompt.strip(), 'warnings': warnings, 'promptModel': PROMPT_MODEL}
