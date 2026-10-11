import { Component, computed, input } from '@angular/core';
import { ProjectStatus } from '../../models/project.model';

@Component({
  selector: 'app-processing-progress',
  templateUrl: './processing-progress.html',
  styleUrl: './processing-progress.scss',
})
export class ProcessingProgressComponent {
  readonly status = input.required<ProjectStatus>();
  readonly uploadPercent = input<number | null>(null);
  readonly enhanceColors = input(true);
  readonly steps = computed(() => [
    'Vídeos recebidos',
    'IA local: avaliar qualidade visual',
    'A analisar nitidez',
    'A analisar exposição',
    'A analisar estabilidade',
    'A selecionar melhores momentos',
    this.enhanceColors() ? 'A melhorar cores e cortar clips' : 'A cortar clips',
    'A criar vídeo final',
  ]);

  phase(index: number): 'done' | 'active' | 'waiting' {
    const key = this.status().stageKey;
    const groups = [0, 1, 1, 1, 1, 2, 3, 4];
    const current =
      (
        { upload: 0, analysis: 1, selection: 2, clips: 3, export: 4, completed: 5 } as Record<
          string,
          number
        >
      )[key] ?? 0;
    return groups[index] < current ? 'done' : groups[index] === current ? 'active' : 'waiting';
  }
}
