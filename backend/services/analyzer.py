import math
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from services.segmentation import find_candidate_windows
from services.scoring import Segment, ai_final_score, final_score
from services.ai_scorer import LocalAestheticScorer, get_ai_scorer


def video_duration(path: Path) -> float:
    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        valid, _ = capture.read()
        duration = frames / fps if fps > 0 else 0
        if not valid or not math.isfinite(duration) or duration <= 0:
            raise ValueError(f'O vídeo {path.name} está corrompido ou não é suportado.')
        return duration
    finally:
        capture.release()


def read_frame(capture: cv2.VideoCapture, seconds: float) -> np.ndarray | None:
    capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    valid, frame = capture.read()
    if not valid:
        return None
    height, width = frame.shape[:2]
    if max(width, height) > 640:
        ratio = 640 / max(width, height)
        frame = cv2.resize(frame, (max(1, round(width * ratio)), max(1, round(height * ratio))))
    return frame


def flow_metrics(first: np.ndarray, second: np.ndarray) -> tuple[np.ndarray, float] | None:
    features = cv2.goodFeaturesToTrack(first, maxCorners=120, qualityLevel=.02, minDistance=8)
    if features is None or len(features) < 6:
        return None
    tracked, status, _ = cv2.calcOpticalFlowPyrLK(first, second, features, None)
    if tracked is None or status is None:
        return None
    mask = status.reshape(-1) == 1
    delta = (tracked - features).reshape(-1, 2)[mask]
    if len(delta) < 6:
        return None
    global_motion = np.median(delta, axis=0)
    residual = float(np.median(np.linalg.norm(delta - global_motion, axis=1)))
    return global_motion, residual


def analyze_video(path: Path, on_progress: Callable[[float], None],
                  ai_scorer: LocalAestheticScorer | None = None) -> list[Segment]:
    scorer = ai_scorer if ai_scorer is not None else get_ai_scorer()
    duration = video_duration(path)
    windows = find_candidate_windows(path, lambda fraction: on_progress(.25 * fraction))
    capture = cv2.VideoCapture(str(path))
    segments: list[Segment] = []
    try:
        for window in windows:
            start, end = window['start'], window['end']
            sharpness_values: list[float] = []
            exposure_values: list[float] = []
            ai_frames: list[np.ndarray] = []
            vectors, residuals = [], []
            # Close pairs (100 ms), spread across the segment: sparse but suitable for LK.
            for sample_index, sample in enumerate(np.linspace(start, max(start, end - .15), 6)):
                color_frame = read_frame(capture, float(sample))
                second_color = read_frame(capture, min(float(sample) + .1, end - .01))
                if color_frame is None:
                    continue
                first = cv2.cvtColor(color_frame, cv2.COLOR_BGR2GRAY)
                second = cv2.cvtColor(second_color, cv2.COLOR_BGR2GRAY) if second_color is not None else None
                if sample_index in (0, 2, 5):
                    ai_frames.append(color_frame)
                laplacian = float(cv2.Laplacian(first, cv2.CV_64F).var())
                sharpness_values.append(100 * laplacian / (laplacian + 150))
                extremes = float(np.mean(first < 16) + np.mean(first > 239))
                balance = min(1., abs(float(first.mean()) - 127.5) / 127.5)
                exposure_values.append(float(np.clip(100 * (1 - .85 * extremes - .15 * balance), 0, 100)))
                if second is not None:
                    flow = flow_metrics(first, second)
                    if flow is not None:
                        vectors.append(flow[0])
                        residuals.append(flow[1])
            if not sharpness_values:
                raise ValueError(f'Não foi possível analisar {path.name}.')
            if vectors:
                velocity = np.array(vectors)
                speed = float(np.median(np.linalg.norm(velocity, axis=1)))
                changes = float(np.median(np.linalg.norm(np.diff(velocity, axis=0), axis=1))) if len(velocity) > 1 else 0
                instability = .9 * changes + .35 * float(np.mean(residuals)) + .3 * max(0, speed - 12)
                stability = float(100 * np.exp(-instability / 5))
                movement = float(100 * (1 - np.exp(-speed / .8)) * np.exp(-max(0, speed - 5) / 10))
            else:
                # Low texture does not prove stability. Use a conservative neutral estimate.
                stability, movement = 50., 0.
            sharpness = float(np.mean(sharpness_values))
            exposure = float(np.mean(exposure_values))
            technical_score = final_score(stability, sharpness, exposure, movement)
            ai = scorer.score_frames(ai_frames)
            segment = Segment(filename=path.name, start=round(start, 4), end=round(end, 4),
                                    sharpness=round(sharpness, 4), exposure=round(exposure, 4),
                                    stability=round(stability, 4), movement=round(movement, 4),
                                    technicalScore=round(technical_score, 6),
                                    score=round(ai_final_score(ai['aiScore'], technical_score), 6), selected=False)
            segment.update(ai)
            segment.update(window)
            segments.append(segment)
            on_progress(.25 + .75 * end / duration)
    finally:
        capture.release()
    return segments
