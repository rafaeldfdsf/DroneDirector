"""Temporal boundaries measured from appearance and camera movement, not narration."""
from pathlib import Path
from typing import Callable
import cv2
import numpy as np


def windows_from_samples(times: list[float], changes: list[float], speeds: list[float],
                         duration: float) -> list[dict]:
    # L1 histogram distance > .65 marks an abrupt appearance change (scale 0..2).
    scenes = [0.] + [t for t, change in zip(times, changes) if change > .65 and 0 < t < duration] + [duration]
    windows = []
    for scene_start, scene_end in zip(scenes, scenes[1:]):
        start = scene_start
        while scene_end - start > .01:
            ceiling = min(start + 8., scene_end)
            if scene_end - start <= 8.:
                end, reason, confidence = scene_end, 'Mudança de cena' if scene_end < duration else 'Fim da tomada', .9
            else:
                options = [(i, t) for i, t in enumerate(times) if start + 3. <= t <= ceiling]
                # Prefer a pause or a local slowdown; avoid fragmenting a continuous pan.
                pauses = [(i, t) for i, t in options if i > 0 and i + 1 < len(speeds)
                          and speeds[i] < .7 * max(speeds[i-1], speeds[i+1], .01)]
                if pauses:
                    i, end = min(pauses, key=lambda p: (speeds[p[0]], abs(p[1]-start-5.)))
                    reason, confidence = 'Pausa de movimento', .7
                else:
                    # A low velocity-change position near five seconds is a safe fallback.
                    i, end = min(options, key=lambda p: abs(speeds[p[0]] - speeds[max(0, p[0]-1)])
                                 + .2 * abs(p[1]-start-5.))
                    reason, confidence = 'Limite temporal suave', .4
            windows.append(dict(start=round(start, 4), end=round(end, 4), cutReason=reason, cutConfidence=confidence))
            start = end
    return windows


def find_candidate_windows(path: Path, on_progress: Callable[[float], None]) -> list[dict]:
    from services.analyzer import video_duration, read_frame, flow_metrics
    duration = video_duration(path)
    capture = cv2.VideoCapture(str(path))
    times, changes, speeds = [], [], []
    previous_hist = None
    try:
        for t in np.arange(0, max(.001, duration-.05), .5):
            frame = read_frame(capture, float(t))
            if frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            histogram = cv2.calcHist([gray], [0], None, [32], [0,256]).reshape(-1)
            histogram /= max(1., float(histogram.sum()))
            changes.append(0. if previous_hist is None else float(np.abs(histogram - previous_hist).sum()))
            nearby = read_frame(capture, min(float(t)+.1, duration-.01))
            flow = flow_metrics(gray, cv2.cvtColor(nearby, cv2.COLOR_BGR2GRAY)) if nearby is not None else None
            speeds.append(float(np.linalg.norm(flow[0])) if flow is not None else 0.)
            times.append(float(t))
            previous_hist = histogram
            on_progress(min(1., (float(t)+.5)/duration))
    finally:
        capture.release()
    if not times:
        raise ValueError(f'Não foi possível encontrar momentos em {path.name}.')
    return windows_from_samples(times, changes, speeds, duration)
