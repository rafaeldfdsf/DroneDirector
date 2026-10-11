import json
import cv2
from models.project import Project, ProcessRequest
from services.scoring import select_segments


def normalize_selection(candidates: list[dict], selected_ids: list[str], duration: int) -> list[dict]:
    lookup = {c['id']: c for c in candidates}
    if not selected_ids:
        raise ValueError('Seleciona pelo menos um momento para exportar.')
    if len(set(selected_ids)) != len(selected_ids) or any(cid not in lookup for cid in selected_ids):
        raise ValueError('A seleção contém momentos inválidos ou repetidos.')
    chosen = [lookup[cid] for cid in selected_ids]
    for index, candidate in enumerate(chosen):
        for previous in chosen[:index]:
            if (candidate['filename'] == previous['filename'] and
                candidate['start'] < previous['end']-.001 and candidate['end'] > previous['start']+.001):
                raise ValueError('Escolhe momentos que não se sobreponham no mesmo vídeo.')
    remaining, effective = float(duration), []
    for candidate in chosen:
        if remaining <= .001:
            break
        item = dict(candidate)
        item['end'] = round(item['start'] + min(item['end']-item['start'], remaining), 4)
        remaining -= item['end']-item['start']
        effective.append(item)
    return effective


def reasons(segment: dict) -> list[str]:
    result = []
    if segment.get('aiScore', 0) >= 60:
        result.append('Estética visual favorável')
    if segment.get('sharpness', 0) >= 70:
        result.append('Boa nitidez')
    if segment.get('stability', 0) >= 70:
        result.append('Movimento estável')
    elif segment.get('stability', 100) < 40:
        result.append('Movimento irregular')
    if segment.get('promptAdjustment', 0) > 1:
        result.append('Correspondência com o prompt')
    result.append(segment.get('cutReason', 'Qualidade visual'))
    return result


def save_review(project: Project, data: dict) -> None:
    path = project.directory/'data'/'review.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def load_review(project: Project) -> dict:
    path = project.directory/'data'/'review.json'
    if not path.is_file():
        raise ValueError('A análise dos momentos ainda não está disponível.')
    return json.loads(path.read_text(encoding='utf-8'))


def public_review(project: Project, data: dict) -> dict:
    def public(candidate):
        item = {k:v for k,v in candidate.items() if k != 'visualEmbedding'}
        base = f'/api/projects/{project.project_id}'
        item.update(reasons=reasons(candidate), thumbnailUrl=f'{base}/thumbnail/{candidate["id"]}',
                    previewUrl=f'{base}/preview/{candidate["id"]}')
        return item
    result = {k:v for k,v in data.items() if k != 'candidates'}
    result['candidates'] = [public(c) for c in data['candidates']]
    result['effectiveSegments'] = [public(c) for c in normalize_selection(data['candidates'], data['selectedIds'], data['duration'])]
    result['effectiveDuration'] = round(sum(c['end']-c['start'] for c in result['effectiveSegments']), 3)
    return result


def build_review(project: Project, segments: list[dict], options: ProcessRequest, metadata: dict) -> dict:
    from services.analyzer import read_frame
    folder = project.directory/'data'/'thumbnails'
    folder.mkdir(exist_ok=True)
    for i, segment in enumerate(segments):
        segment['id'] = f'm{i:05d}'
        capture = cv2.VideoCapture(str(project.directory/'original'/segment['filename']))
        try:
            frame = read_frame(capture, (segment['start']+segment['end'])/2)
            if frame is None or not cv2.imwrite(str(folder/f'{segment["id"]}.jpg'), frame):
                raise ValueError('Não foi possível criar a miniatura de um momento.')
        finally:
            capture.release()
    selected = select_segments(segments, options.duration, project.files)
    if not selected:
        raise ValueError('Não foram encontrados momentos utilizáveis.')
    data = dict(candidates=segments, suggestedIds=[s['id'] for s in selected],
                selectedIds=[s['id'] for s in selected], duration=options.duration,
                enhanceColors=options.enhanceColors, **metadata)
    save_review(project, data)
    return data
