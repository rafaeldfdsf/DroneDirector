import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = Path(os.getenv('DRONE_PROJECTS_DIR', str(ROOT_DIR / 'projects')))
FFMPEG = os.getenv('FFMPEG_PATH', 'ffmpeg')
FFPROBE = os.getenv('FFPROBE_PATH', 'ffprobe')
CORS_ORIGINS = ['http://localhost:4200', 'http://127.0.0.1:4200']
SEGMENT_SECONDS = 5.0
MAX_FILE_BYTES = 20 * 1024**3
MAX_FILES = 50
AI_MODELS_DIR = Path(os.getenv('DRONE_AI_MODELS_DIR', str(ROOT_DIR / 'backend' / 'ai_models')))
