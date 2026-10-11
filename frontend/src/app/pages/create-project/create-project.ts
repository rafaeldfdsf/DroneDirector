import { Component, DestroyRef, inject, signal } from '@angular/core';
import { HttpErrorResponse, HttpEventType } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  catchError,
  EMPTY,
  exhaustMap,
  filter,
  Subscription,
  switchMap,
  take,
  takeWhile,
  timeout,
  timer,
} from 'rxjs';
import { VideoUploadComponent } from '../../components/video-upload/video-upload';
import { ProcessingProgressComponent } from '../../components/processing-progress/processing-progress';
import { VideoResultComponent } from '../../components/video-result/video-result';
import {
  ProcessOptions,
  ProjectStatus,
  ReviewData,
  ExportOptions,
} from '../../models/project.model';
import { MomentReviewComponent } from '../../components/moment-review/moment-review';
import { VideoService } from '../../services/video.service';

@Component({
  selector: 'app-create-project',
  imports: [
    VideoUploadComponent,
    ProcessingProgressComponent,
    VideoResultComponent,
    MomentReviewComponent,
  ],
  templateUrl: './create-project.html',
  styleUrl: './create-project.scss',
})
export class CreateProjectComponent {
  readonly service = inject(VideoService);
  private readonly destroyRef = inject(DestroyRef);
  private polling?: Subscription;
  readonly files = signal<File[]>([]);
  readonly duration = signal<15 | 30 | 60>(30);
  readonly enhance = signal(true);
  readonly screen = signal<'upload' | 'processing' | 'review' | 'result'>('upload');
  readonly prompt = signal('');
  readonly review = signal<ReviewData | null>(null);
  readonly reviewLoadFailed = signal(false);
  readonly busy = signal(false);
  readonly error = signal('');
  readonly connectionLost = signal(false);
  readonly uploadPercent = signal<number | null>(null);
  readonly status = signal<ProjectStatus>({
    projectId: '',
    status: 'created',
    progress: 0,
    stage: '',
    stageKey: 'upload',
    error: null,
    duration: 0,
    selectedMoments: 0,
    videos: 0,
  });
  readonly durations = [15, 30, 60] as const;

  addFiles(incoming: File[]): void {
    this.error.set('');
    const valid: File[] = [];
    for (const file of incoming) {
      if (!/\.(mp4|mov)$/i.test(file.name)) {
        this.error.set(`O ficheiro ${file.name} não é suportado. Seleciona vídeos MP4 ou MOV.`);
      } else if (!file.size) {
        this.error.set(`O ficheiro ${file.name} está vazio.`);
      } else if (file.size > 20 * 1024 ** 3) {
        this.error.set(`O ficheiro ${file.name} excede o limite de 20 GB.`);
      } else if (
        ![...this.files(), ...valid].some(
          (item) =>
            item.name === file.name &&
            item.size === file.size &&
            item.lastModified === file.lastModified,
        )
      ) {
        valid.push(file);
      }
    }
    if (this.files().length + valid.length > 50) {
      this.error.set('Seleciona no máximo 50 vídeos.');
      return;
    }
    this.files.update((current) => [...current, ...valid]);
  }

  removeFile(index: number): void {
    this.files.update((current) => current.filter((_, i) => i !== index));
  }

  create(): void {
    if (this.busy()) return;
    if (!this.files().length) {
      this.error.set('Seleciona pelo menos um vídeo.');
      return;
    }
    this.error.set('');
    this.connectionLost.set(false);
    this.busy.set(true);
    this.uploadPercent.set(null);
    this.screen.set('processing');
    this.status.update((current) => ({
      ...current,
      progress: 0,
      status: 'uploading',
      stage: 'A criar o projeto…',
      stageKey: 'upload',
    }));
    const options: ProcessOptions = {
      duration: this.duration(),
      enhanceColors: this.enhance(),
      prompt: this.prompt(),
    };
    this.service
      .createProject()
      .pipe(
        timeout(15000),
        switchMap((project) => {
          this.status.update((current) => ({
            ...current,
            projectId: project.projectId,
            stage: 'A enviar vídeos…',
          }));
          return this.service.uploadVideos(project.projectId, this.files());
        }),
        filter((event) => {
          if (event.type === HttpEventType.UploadProgress) {
            this.uploadPercent.set(
              event.total ? Math.round((100 * event.loaded) / event.total) : null,
            );
            if (event.total && event.loaded === event.total)
              this.status.update((current) => ({
                ...current,
                stage: 'A validar os vídeos recebidos…',
              }));
          }
          return event.type === HttpEventType.Response;
        }),
        take(1),
        switchMap(() => {
          this.status.update((current) => ({
            ...current,
            status: 'queued',
            progress: 5,
            stage: 'A iniciar processamento…',
            stageKey: 'analysis',
          }));
          return this.service.analyze(this.status().projectId, options).pipe(timeout(15000));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => this.poll(),
        error: (error: unknown) => {
          this.error.set(this.message(error));
          this.busy.set(false);
          const uncertainResponse = !(error instanceof HttpErrorResponse) || error.status === 0;
          if (this.status().status === 'queued' && uncertainResponse) {
            this.connectionLost.set(true);
          } else {
            this.screen.set('upload');
          }
        },
      });
  }

  poll(): void {
    this.polling?.unsubscribe();
    this.connectionLost.set(false);
    this.error.set('');
    this.busy.set(true);
    let failures = 0;
    this.polling = timer(0, 1200)
      .pipe(
        exhaustMap(() =>
          this.service.getStatus(this.status().projectId).pipe(
            timeout(10000),
            catchError((error: unknown) => {
              failures += 1;
              this.error.set('A ligação ao backend foi interrompida. A tentar novamente…');
              if (failures >= 5 || (error instanceof HttpErrorResponse && error.status === 404)) {
                this.polling?.unsubscribe();
                this.busy.set(false);
                this.connectionLost.set(true);
                this.error.set(this.message(error));
              }
              return EMPTY;
            }),
          ),
        ),
        takeWhile(
          (current) =>
            !['completed', 'failed', 'created', 'ready', 'review'].includes(current.status),
          true,
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((current) => {
        failures = 0;
        this.error.set('');
        this.status.set(current);
        if (current.status === 'review') {
          this.loadReview();
        } else if (current.status === 'completed') {
          this.busy.set(false);
          this.screen.set('result');
        } else if (current.status === 'failed') {
          this.error.set(current.error || 'O processamento falhou.');
          this.busy.set(false);
        } else if (current.status === 'created' || current.status === 'ready') {
          this.busy.set(false);
          this.screen.set('upload');
          this.error.set('O processamento não chegou a começar. Podes tentar novamente.');
        }
      });
  }

  reset(): void {
    this.polling?.unsubscribe();
    this.screen.set('upload');
    this.files.set([]);
    this.busy.set(false);
    this.error.set('');
    this.connectionLost.set(false);
    this.prompt.set('');
    this.review.set(null);
    this.reviewLoadFailed.set(false);
  }

  loadReview(): void {
    this.busy.set(true);
    this.reviewLoadFailed.set(false);
    this.service
      .getReview(this.status().projectId)
      .pipe(timeout(15000), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.review.set(data);
          this.screen.set('review');
          this.busy.set(false);
          this.error.set(this.status().error || '');
        },
        error: (error) => {
          this.busy.set(false);
          this.reviewLoadFailed.set(true);
          this.error.set(this.message(error));
        },
      });
  }

  suggest(prompt: string): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.service
      .suggest(this.status().projectId, prompt)
      .pipe(timeout(30000), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.review.set(data);
          this.busy.set(false);
        },
        error: (error) => {
          this.error.set(this.message(error));
          this.busy.set(false);
        },
      });
  }

  export(options: ExportOptions): void {
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    this.service
      .export(this.status().projectId, options)
      .pipe(timeout(15000), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.screen.set('processing');
          this.status.update((current) => ({
            ...current,
            status: 'exporting',
            stageKey: 'clips',
            stage: 'A iniciar exportação…',
          }));
          this.poll();
        },
        error: (error) => {
          this.error.set(this.message(error));
          this.busy.set(false);
          if (!(error instanceof HttpErrorResponse) || error.status === 0) {
            this.screen.set('processing');
            this.connectionLost.set(true);
          }
        },
      });
  }

  private message(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (typeof error.error?.detail === 'string') return error.error.detail;
      if (error.status === 0)
        return 'Não foi possível contactar o backend. Confirma que está a funcionar em localhost:8000.';
      if (error.status === 422)
        return 'Os dados enviados não são válidos. Verifica os vídeos e a duração.';
    }
    return 'Não foi possível concluir o pedido. Verifica a ligação ao backend e tenta novamente.';
  }
}
