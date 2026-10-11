export type ProjectState =
  | 'created'
  | 'uploading'
  | 'ready'
  | 'queued'
  | 'processing'
  | 'analyzing'
  | 'review'
  | 'exporting'
  | 'completed'
  | 'failed';

export interface ProjectStatus {
  projectId: string;
  status: ProjectState;
  progress: number;
  stage: string;
  stageKey: string;
  error: string | null;
  duration: number;
  selectedMoments: number;
  videos: number;
  selectionMethod?: 'local-ai';
  aiModel?: string | null;
  aiScore?: number | null;
}

export interface ProcessOptions {
  duration: 15 | 30 | 60;
  enhanceColors: boolean;
  prompt?: string;
}

export interface MomentCandidate {
  id: string;
  filename: string;
  start: number;
  end: number;
  score: number;
  aiScore: number;
  reasons: string[];
  thumbnailUrl: string;
  previewUrl: string;
}

export interface ReviewData {
  candidates: MomentCandidate[];
  suggestedIds: string[];
  selectedIds: string[];
  effectiveSegments: MomentCandidate[];
  effectiveDuration: number;
  duration: 15 | 30 | 60;
  enhanceColors: boolean;
  prompt: string;
  warnings: string[];
}

export interface ExportOptions extends ProcessOptions {
  selectedIds: string[];
}
