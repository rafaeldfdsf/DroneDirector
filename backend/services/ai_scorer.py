"""Local learned aesthetic scoring. Inference has no network or remote-code calls."""
import hashlib
import os
import zipfile
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

import config

MODEL_NAME = 'CLIP ViT-B/32 + LAION Aesthetic V1 (ONNX int8)'
VISION_FILENAME = 'clip-vit-b32-vision-int8.onnx'
HEAD_FILENAME = 'laion-v1-vit-b32-linear.pth'
VISION_SIZE = 89_117_001
VISION_SHA256 = '583fd1110a514667812fee7d684952aaf82a99b959760c8d7dca7e0ab9839299'
HEAD_SHA256 = 'c7b14cead230694acc7b9447974d3cad78003c72da032e402a303b6c2429e85f'
CLIP_REVISION = 'd15189d7028b43f1d3e65039190477f6af591c2a'
LAION_REVISION = '6d122adad522ab246644d9dc1c6d7a3810ee255f'
VISION_URL = f'https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/{CLIP_REVISION}/onnx/vision_model_quantized.onnx'
HEAD_URL = f'https://raw.githubusercontent.com/LAION-AI/aesthetic-predictor/{LAION_REVISION}/sa_0_4_vit_b_32_linear.pth'
MODEL_ERROR = 'O modelo de IA local está ausente ou corrompido. No backend, executa .\\.venv\\Scripts\\python.exe setup_ai.py.'
MEAN = np.array([.48145466, .4578275, .40821073], dtype=np.float32)
STD = np.array([.26862954, .26130258, .27577711], dtype=np.float32)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def check_model_files(directory: Path | None = None) -> None:
    location = directory if directory is not None else config.AI_MODELS_DIR
    vision = location / VISION_FILENAME
    head = location / HEAD_FILENAME
    if not vision.is_file() or not head.is_file() or vision.stat().st_size != VISION_SIZE:
        raise ValueError(MODEL_ERROR)
    for path, expected in ((vision, VISION_SHA256), (head, HEAD_SHA256)):
        stat = path.stat()
        if _cached_digest(str(path.resolve()), stat.st_size, stat.st_mtime_ns) != expected:
            raise ValueError(MODEL_ERROR)


@lru_cache(maxsize=8)
def _cached_digest(path: str, size: int, modified_ns: int) -> str:
    # Cache only while both size and modification time stay unchanged.
    return file_sha256(Path(path))


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    if frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
        raise ValueError('Não foi possível analisar uma imagem do vídeo com IA.')
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    width, height = image.size
    if width < height:
        size = (224, int(224 * height / width))
    else:
        size = (int(224 * width / height), 224)
    image = image.resize(size, resample=Image.Resampling.BICUBIC)
    left, top = (size[0] - 224) // 2, (size[1] - 224) // 2
    image = image.crop((left, top, left + 224, top + 224))
    pixels = np.asarray(image, dtype=np.float32) / 255.
    return np.ascontiguousarray(((pixels - MEAN) / STD).transpose(2, 0, 1))


def load_aesthetic_head(path: Path) -> tuple[np.ndarray, float]:
    if file_sha256(path) != HEAD_SHA256:
        raise ValueError(MODEL_ERROR)
    # The pinned checkpoint is a linear 512->1 head. Read its verified raw storages;
    # never execute its pickle payload or load remote Python code.
    with zipfile.ZipFile(path) as archive:
        weight = np.frombuffer(archive.read('archive/data/0'), dtype='<f4').copy()
        bias = np.frombuffer(archive.read('archive/data/1'), dtype='<f4')
    if weight.shape != (512,) or bias.shape != (1,) or not np.isfinite(weight).all() or not np.isfinite(bias).all():
        raise ValueError(MODEL_ERROR)
    return weight, float(bias[0])


class LocalAestheticScorer:
    def __init__(self, directory: Path):
        check_model_files(directory)
        vision = directory / VISION_FILENAME
        if file_sha256(vision) != VISION_SHA256:
            raise ValueError(MODEL_ERROR)
        self.weight, self.bias = load_aesthetic_head(directory / HEAD_FILENAME)
        options = ort.SessionOptions()
        options.intra_op_num_threads = min(4, max(1, (os.cpu_count() or 2) - 1))
        options.inter_op_num_threads = 1
        options.log_severity_level = 3
        ort.disable_telemetry_events()
        try:
            self.session = ort.InferenceSession(str(vision), sess_options=options, providers=['CPUExecutionProvider'])
        except Exception as error:
            raise ValueError(MODEL_ERROR) from error

    def score_frames(self, frames: list[np.ndarray]) -> dict:
        if not frames:
            raise ValueError('Não foram encontrados frames utilizáveis para a IA.')
        pixels = np.stack([preprocess_frame(frame) for frame in frames])
        try:
            features = self.session.run(['image_embeds'], {'pixel_values': pixels})[0].astype(np.float32)
        except Exception as error:
            raise RuntimeError('A análise com IA local falhou. Consulta o terminal do backend.') from error
        if features.shape != (len(frames), 512) or not np.isfinite(features).all():
            raise ValueError('O modelo de IA local devolveu dados inválidos.')
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        if np.any(norms < 1e-8):
            raise ValueError('O modelo de IA local não conseguiu analisar estas imagens.')
        features /= norms
        raw = features @ self.weight + self.bias
        scores = np.clip(raw * 10, 0, 100)
        average = np.mean(features, axis=0)
        average /= max(float(np.linalg.norm(average)), 1e-8)
        return {'aiScore': round(float(np.mean(scores)), 6),
                'aiFrameScores': [round(float(value), 6) for value in scores],
                'aiModel': MODEL_NAME, 'visualEmbedding': average.tolist()}


@lru_cache(maxsize=1)
def _cached_scorer(directory: str) -> LocalAestheticScorer:
    return LocalAestheticScorer(Path(directory))


def get_ai_scorer() -> LocalAestheticScorer:
    return _cached_scorer(str(config.AI_MODELS_DIR.resolve()))
