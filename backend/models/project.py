from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Literal

from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    duration: Literal[15, 30, 60] = 30
    enhanceColors: bool = True
    prompt: str = Field(default='', max_length=500)


class ExportRequest(ProcessRequest):
    selectedIds: list[str] = Field(max_length=1000)


class SuggestRequest(BaseModel):
    prompt: str = Field(default='', max_length=500)


@dataclass
class Project:
    project_id: str
    directory: Path
    files: list[str] = field(default_factory=list)
    status: str = 'created'
    progress: int = 0
    stage: str = 'Selecionar vídeos'
    stage_key: str = 'upload'
    error: str | None = None
    duration: float = 0
    selected_moments: int = 0
    ai_model: str | None = None
    ai_score: float | None = None

    def snapshot(self) -> dict:
        return {'projectId': self.project_id, 'status': self.status,
                'progress': self.progress, 'stage': self.stage, 'stageKey': self.stage_key,
                'error': self.error, 'duration': self.duration,
                'selectedMoments': self.selected_moments, 'videos': len(self.files),
                'selectionMethod': 'local-ai', 'aiModel': self.ai_model, 'aiScore': self.ai_score}


store: dict[str, Project] = {}
store_lock = RLock()


def update(project: Project, **changes: object) -> None:
    with store_lock:
        for name, value in changes.items():
            setattr(project, name, value)
