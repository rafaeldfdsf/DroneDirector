import json
import logging
import shutil
import subprocess
from pathlib import Path

import config
from services.color_enhancer import color_filter

logger = logging.getLogger(__name__)


def check_ffmpeg() -> None:
    if not shutil.which(config.FFMPEG) or not shutil.which(config.FFPROBE):
        raise ValueError('FFmpeg ou ffprobe indisponível. Consulta as instruções no README.')


def run_ffmpeg(arguments: list[str]) -> None:
    result = subprocess.run([config.FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', *arguments],
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
    if result.returncode:
        logger.error('FFmpeg falhou: %s', result.stderr)
        raise RuntimeError('Não foi possível criar o vídeo final. Verifica se as filmagens são suportadas.')


def extract_clip(source: Path, output: Path, start: float, duration: float, enhance: bool) -> None:
    filters = ['scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2',
               'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black', 'setsar=1', 'fps=30']
    correction = color_filter(enhance)
    if correction:
        filters.append(correction)
    run_ffmpeg(['-ss', str(start), '-i', str(source), '-t', str(duration), '-map', '0:v:0',
                '-vf', ','.join(filters), '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                '-pix_fmt', 'yuv420p', '-threads', '2', '-movflags', '+faststart', str(output)])


def concatenate(clips: list[Path], output: Path) -> float:
    manifest = clips[0].parent / 'concat.txt'
    # Only generated ASCII clip names enter the manifest; original filenames never do.
    manifest.write_text(''.join(f"file '{clip.name}'\n" for clip in clips), encoding='utf-8')
    run_ffmpeg(['-f', 'concat', '-safe', '1', '-i', str(manifest), '-c', 'copy', '-movflags', '+faststart', str(output)])
    probe = subprocess.run([config.FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
                            '-of', 'json', str(output)], capture_output=True, text=True, check=True, timeout=30)
    return float(json.loads(probe.stdout)['format']['duration'])
