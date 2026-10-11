import logging
import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

import config
from models.project import ProcessRequest, ExportRequest, SuggestRequest, Project, store, store_lock, update
from services.analyzer import video_duration
from services.processor import executor, process_project, analyze_project, export_project
from services.review import load_review, public_review, normalize_selection, save_review
from services.prompt_scorer import check_prompt_model_files, apply_prompt
from services.scoring import select_segments
from services.video_editor import run_ffmpeg
from threading import Lock
from services.video_editor import check_ffmpeg
from services.ai_scorer import check_model_files

router = APIRouter(prefix='/api/projects', tags=['Projetos'])
logger = logging.getLogger(__name__)
preview_lock = Lock()


def get_project(project_id: str) -> Project:
    try:
        canonical = str(UUID(project_id))
    except ValueError:
        raise HTTPException(404, 'Projeto não encontrado.')
    with store_lock:
        project = store.get(canonical)
    if project is None:
        raise HTTPException(404, 'Projeto não encontrado. O backend pode ter sido reiniciado.')
    return project


@router.post('')
def create_project() -> dict:
    project_id = str(uuid4())
    directory = config.PROJECTS_DIR / project_id
    for child in ['original', 'clips', 'data', 'output']:
        (directory / child).mkdir(parents=True, exist_ok=True)
    with store_lock:
        store[project_id] = Project(project_id, directory)
    return {'projectId': project_id}


@router.post('/{project_id}/videos')
async def upload_videos(project_id: str, videos: list[UploadFile] = File(...)) -> dict:
    project = get_project(project_id)
    with store_lock:
        if project.status not in ('created', 'ready'):
            raise HTTPException(409, 'Este projeto já está a receber ou processar vídeos.')
        if len(project.files) + len(videos) > config.MAX_FILES:
            raise HTTPException(400, f'Seleciona no máximo {config.MAX_FILES} vídeos.')
        old_status = project.status
        project.status = 'uploading'
    saved: list[Path] = []
    try:
        for upload in videos:
            raw_name = (upload.filename or '').replace('\\', '/').split('/')[-1]
            extension = Path(raw_name).suffix.lower()
            if extension not in ('.mp4', '.mov'):
                raise HTTPException(400, 'Formato não suportado. Seleciona vídeos MP4 ou MOV.')
            stem = re.sub(r'[^\w .-]', '_', Path(raw_name).stem).strip(' .')[:100] or 'video'
            if re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', stem, flags=re.IGNORECASE):
                stem = f'video_{stem}'
            name = f'{stem}{extension}'
            suffix = 1
            while (project.directory / 'original' / name).exists():
                name = f'{stem}_{suffix}{extension}'
                suffix += 1
            path = project.directory / 'original' / name
            saved.append(path)
            size = 0
            with path.open('wb') as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > config.MAX_FILE_BYTES:
                        raise HTTPException(413, 'Cada vídeo pode ter no máximo 20 GB.')
                    await run_in_threadpool(destination.write, chunk)
            if size == 0:
                raise HTTPException(400, f'O ficheiro {raw_name} está vazio.')
            try:
                await run_in_threadpool(video_duration, path)
            except ValueError:
                raise HTTPException(400, f'O vídeo {raw_name} está corrompido ou não é suportado.')
        with store_lock:
            project.files.extend(path.name for path in saved)
            update(project, status='ready', progress=5, stage='Vídeos recebidos', stage_key='upload')
        return {'projectId': project_id, 'videos': project.files}
    except Exception:
        for path in saved:
            path.unlink(missing_ok=True)
        update(project, status=old_status)
        raise
    finally:
        for upload in videos:
            await upload.close()


@router.post('/{project_id}/process', status_code=202)
def start_processing(project_id: str, request: ProcessRequest) -> dict:
    project = get_project(project_id)
    with store_lock:
        if project.status not in ('created', 'ready'):
            raise HTTPException(409, 'Este projeto já está a processar ou terminou. Cria outro projeto.')
        if not project.files:
            raise HTTPException(400, 'Seleciona pelo menos um vídeo.')
        try:
            check_ffmpeg()
            check_model_files()
            if request.prompt.strip():
                check_prompt_model_files()
        except ValueError as error:
            raise HTTPException(503, str(error))
        update(project, status='queued', stage='A aguardar processamento', stage_key='analysis', error=None)
        executor.submit(process_project, project, request)
    return {'projectId': project_id, 'status': 'queued'}


@router.get('/{project_id}/status')
def project_status(project_id: str) -> dict:
    with store_lock:
        return get_project(project_id).snapshot()


@router.get('/{project_id}/result')
def project_result(project_id: str, download: bool = Query(False)) -> FileResponse:
    project = get_project(project_id)
    path = project.directory / 'output' / 'final.mp4'
    if project.status not in ('completed', 'review', 'exporting') or not path.is_file():
        raise HTTPException(409, 'O vídeo ainda não está disponível.')
    return FileResponse(path, media_type='video/mp4', filename='final.mp4',
                        content_disposition_type='attachment' if download else 'inline')


@router.post('/{project_id}/analyze', status_code=202)
def start_analysis(project_id: str, request: ProcessRequest) -> dict:
    project = get_project(project_id)
    with store_lock:
        if project.status not in ('created', 'ready'):
            raise HTTPException(409, 'Este projeto já está a analisar ou foi analisado.')
        if not project.files:
            raise HTTPException(400, 'Seleciona pelo menos um vídeo.')
        try:
            check_ffmpeg()
            check_model_files()
            if request.prompt.strip():
                check_prompt_model_files()
        except ValueError as error:
            raise HTTPException(503, str(error))
        update(project, status='queued', stage='A aguardar análise', stage_key='analysis', error=None)
        executor.submit(analyze_project, project, request)
    return {'projectId':project_id,'status':'queued'}


@router.get('/{project_id}/review')
def get_review(project_id: str) -> dict:
    project = get_project(project_id)
    try:
        return public_review(project, load_review(project))
    except ValueError as error:
        raise HTTPException(409, str(error))


@router.post('/{project_id}/suggest')
def suggest_moments(project_id: str, request: SuggestRequest) -> dict:
    project = get_project(project_id)
    with store_lock:
        if project.status not in ('review', 'completed'):
            raise HTTPException(409, 'Espera pela análise ou exportação antes de aplicar o prompt.')
        previous_status = project.status
        update(project,status='analyzing',stage='Aplicar orientação extra',stage_key='selection')
    try:
        data = load_review(project)
        metadata = apply_prompt(data['candidates'], request.prompt)
        selected = select_segments(data['candidates'], data['duration'], project.files)
        data.update(metadata, suggestedIds=[s['id'] for s in selected],selectedIds=[s['id'] for s in selected])
        save_review(project,data)
        update(project,status='review',error=None,stage='Momentos prontos para revisão',stage_key='review')
        return public_review(project,data)
    except ValueError as error:
        update(project,status=previous_status)
        raise HTTPException(503, str(error))
    except Exception:
        update(project,status=previous_status)
        raise


@router.post('/{project_id}/export',status_code=202)
def start_export(project_id: str, request: ExportRequest) -> dict:
    project = get_project(project_id)
    with store_lock:
        if project.status not in ('review','completed'):
            raise HTTPException(409, 'Este projeto ainda não está pronto para exportar ou já está a exportar.')
        try:
            data = load_review(project)
            normalize_selection(data['candidates'], request.selectedIds, request.duration)
            check_ffmpeg()
        except ValueError as error:
            raise HTTPException(400, str(error))
        update(project,status='exporting',stage='A aguardar exportação',stage_key='clips',error=None)
        executor.submit(export_project,project,request.selectedIds,request)
    return {'projectId':project_id,'status':'exporting'}


def candidate_for(project: Project, candidate_id: str) -> dict:
    try:
        data = load_review(project)
    except ValueError:
        raise HTTPException(409, 'A análise ainda não está disponível.')
    candidate = next((c for c in data['candidates'] if c['id']==candidate_id),None)
    if candidate is None:
        raise HTTPException(404, 'Momento não encontrado neste projeto.')
    return candidate


@router.get('/{project_id}/thumbnail/{candidate_id}')
def thumbnail(project_id: str, candidate_id: str) -> FileResponse:
    project = get_project(project_id)
    candidate_for(project,candidate_id)
    return FileResponse(project.directory/'data'/'thumbnails'/f'{candidate_id}.jpg',media_type='image/jpeg')


@router.get('/{project_id}/preview/{candidate_id}')
def preview(project_id: str, candidate_id: str) -> FileResponse:
    project = get_project(project_id)
    candidate = candidate_for(project,candidate_id)
    folder = project.directory/'data'/'previews'
    folder.mkdir(exist_ok=True)
    output = folder/f'{candidate_id}.mp4'
    # Always create a small browser-compatible derivative: works for MOV/HEVC sources too.
    with preview_lock:
        if not output.is_file():
            temporary = folder/f'{candidate_id}.tmp.mp4'
            run_ffmpeg(['-ss',str(candidate['start']),'-i',str(project.directory/'original'/candidate['filename']),
                        '-t',str(candidate['end']-candidate['start']),'-map','0:v:0','-an',
                        '-vf','scale=640:360:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1,fps=30',
                        '-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-threads','2',
                        '-movflags','+faststart',str(temporary)])
            temporary.replace(output)
    return FileResponse(output,media_type='video/mp4')
