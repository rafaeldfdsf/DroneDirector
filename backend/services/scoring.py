from collections import Counter
import math
from typing import TypedDict


class Segment(TypedDict, total=False):
    filename: str
    start: float
    end: float
    sharpness: float
    exposure: float
    stability: float
    movement: float
    score: float
    selected: bool
    technicalScore: float
    aiScore: float
    aiFrameScores: list[float]
    aiModel: str
    visualEmbedding: list[float]


def final_score(stability: float, sharpness: float, exposure: float, movement: float) -> float:
    return stability * .40 + sharpness * .30 + exposure * .20 + movement * .10


def ai_final_score(ai_score: float, technical_score: float) -> float:
    if not all(math.isfinite(value) and 0 <= value <= 100 for value in (ai_score, technical_score)):
        raise ValueError('A análise devolveu uma pontuação inválida.')
    return ai_score * .70 + technical_score * .30


def visual_repetition_penalty(candidate: Segment, chosen: list[Segment]) -> float:
    embedding = candidate.get('visualEmbedding', [])
    if not embedding:
        return 0.
    similarities = [sum(a * b for a, b in zip(embedding, previous['visualEmbedding']))
                    for previous in chosen if len(previous.get('visualEmbedding', [])) == len(embedding)]
    similarity = max(similarities, default=0.)
    # Soft penalty only: similar scenes remain usable when needed for the requested duration.
    return 8 * min(1., max(0., (similarity - .92) / .08))


def select_segments(segments: list[Segment], duration: int, filenames: list[str]) -> list[Segment]:
    for segment in segments:
        segment['selected'] = False
    chosen: list[Segment] = []
    remaining = sorted(segments, key=lambda item: item['score'], reverse=True)
    counts: Counter[str] = Counter()
    seconds = 0.0
    while remaining and seconds < duration - .001:
        pool = [candidate for candidate in remaining if not any(
            candidate['filename'] == previous['filename'] and
            candidate['start'] < previous['end'] - .001 and
            candidate['end'] > previous['start'] + .001 for previous in chosen)]
        if not pool:
            break
        best = max(pool, key=lambda item: item['score'] + item.get('promptAdjustment', 0.)
                   - visual_repetition_penalty(item, chosen) - min(6, 2 * counts[item['filename']]))
        remaining.remove(best)
        best['selected'] = True
        chosen.append(best)
        counts[best['filename']] += 1
        seconds += best['end'] - best['start']
    # Predictable montage: upload order, then original chronology, never score order.
    order = {name: i for i, name in enumerate(filenames)}
    return sorted(chosen, key=lambda item: (order[item['filename']], item['start']))
