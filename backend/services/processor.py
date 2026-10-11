import json
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from models.project import ProcessRequest, Project, update
from services.analyzer import analyze_video
from services.video_editor import check_ffmpeg, concatenate, extract_clip
from services.ai_scorer import CLIP_REVISION, LAION_REVISION, MODEL_NAME, get_ai_scorer
from services.prompt_scorer import apply_prompt
from services.review import build_review, load_review, normalize_selection, save_review

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='drone-render')


def failure(project: Project, error: Exception, review=False) -> None:
    logger.exception('Falha no projeto %s', project.project_id)
    message = str(error) if isinstance(error, (ValueError, RuntimeError)) else 'O processamento falhou. Consulta o terminal do backend.'
    update(project, status='review' if review else 'failed', stage='Revê a seleção e tenta novamente' if review else 'O processamento falhou',
           stage_key='review' if review else 'failed', error=message)


def analyze_project(project: Project, request: ProcessRequest, automatic=False) -> None:
    try:
        check_ffmpeg()
        update(project, status='processing' if automatic else 'analyzing', progress=8,
               stage='Carregar o modelo de IA local', stage_key='analysis', error=None)
        scorer = get_ai_scorer()
        update(project, ai_model=MODEL_NAME)
        videos, all_segments = [], []
        for index, filename in enumerate(project.files):
            def progress(fraction):
                update(project, progress=10 + int(50*(index+fraction)/len(project.files)),
                       stage=f'Analisar cenas, movimento e qualidade · {index+1}/{len(project.files)}', stage_key='analysis')
            segments = analyze_video(project.directory/'original'/filename, progress, scorer)
            videos.append({'filename':filename,'segments':segments})
            all_segments.extend(segments)
        update(project, progress=65, stage='Aplicar prompt e selecionar momentos', stage_key='selection')
        metadata = apply_prompt(all_segments, request.prompt)
        data = build_review(project, all_segments, request, metadata)
        clean_videos = [dict(filename=v['filename'],segments=[{k:x for k,x in s.items() if k!='visualEmbedding'} for s in v['segments']]) for v in videos]
        (project.directory/'data'/'analysis.json').write_text(json.dumps(dict(videos=clean_videos,
            requestedDuration=request.duration, enhanceColors=request.enhanceColors, prompt=request.prompt,
            selectionMethod='local-ai', scoreWeights={'ai':.7,'technical':.3},
            ai={'model':MODEL_NAME,'device':'CPU','frameSamplesPerSegment':3,
                'clipRevision':CLIP_REVISION,'aestheticRevision':LAION_REVISION}),ensure_ascii=False,indent=2),encoding='utf-8')
        if automatic:
            export_project(project, data['selectedIds'], request, automatic=True)
        else:
            update(project, status='review', progress=70, stage='Momentos prontos para revisão', stage_key='review')
    except Exception as error:
        failure(project, error)


def export_project(project: Project, selected_ids: list[str], request: ProcessRequest, automatic=False) -> None:
    try:
        data = load_review(project)
        selected = normalize_selection(data['candidates'], selected_ids, request.duration)
        # Working selection is independent of the last successful export.
        data.update(selectedIds=[s['id'] for s in selected],duration=request.duration,enhanceColors=request.enhanceColors)
        save_review(project,data)
        update(project, status='processing' if automatic else 'exporting', error=None)
        clips = []
        for index, segment in enumerate(selected):
            update(project, progress=70+int(22*index/len(selected)), stage=f'Cortar momentos · {index+1}/{len(selected)}', stage_key='clips')
            clip = project.directory/'clips'/f'clip_{index+1:03d}.mp4'
            extract_clip(project.directory/'original'/segment['filename'],clip,segment['start'],segment['end']-segment['start'],request.enhanceColors)
            clips.append(clip)
        update(project, progress=95, stage='Criar vídeo final', stage_key='export')
        temporary = project.directory/'output'/'rendering.mp4'
        duration = concatenate(clips, temporary)
        manifest = project.directory/'output'/'export.json'
        manifest_temp = manifest.with_suffix('.tmp')
        manifest_temp.write_text(json.dumps({'segments':[{k:s[k] for k in ('id','filename','start','end')} for s in selected],
                                             'duration':duration}),encoding='utf-8')
        final = project.directory/'output'/'final.mp4'
        backup = project.directory/'output'/'previous.mp4'
        had_previous = final.is_file()
        if had_previous:
            shutil.copy2(final,backup)
        published = False
        try:
            temporary.replace(final)
            published = True
            manifest_temp.replace(manifest)
        except Exception:
            if published:
                if had_previous:
                    backup.replace(final)
                else:
                    final.unlink(missing_ok=True)
            raise
        try:
            backup.unlink(missing_ok=True)
        except OSError:
            logger.warning('Não foi possível remover a cópia anterior de %s', project.project_id)
        update(project,status='completed',progress=100,stage='Concluído',stage_key='completed',duration=round(duration,2),
               selected_moments=len(selected),ai_score=round(sum(s['aiScore'] for s in selected)/len(selected),1))
    except Exception as error:
        failure(project,error,review=not automatic)


def process_project(project: Project, request: ProcessRequest) -> None:
    analyze_project(project, request, automatic=True)
