import { Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { ExportOptions, MomentCandidate, ReviewData } from '../../models/project.model';
import { VideoService } from '../../services/video.service';

@Component({
  selector: 'app-moment-review',
  imports: [DecimalPipe],
  templateUrl: './moment-review.html',
  styleUrl: './moment-review.scss',
})
export class MomentReviewComponent {
  readonly data = input.required<ReviewData>();
  readonly busy = input(false);
  readonly exportRequested = output<ExportOptions>();
  readonly promptRequested = output<string>();
  readonly service = inject(VideoService);
  readonly ids = signal<string[]>([]);
  readonly prompt = signal('');
  readonly replacement = signal<string | null>(null);
  readonly preview = signal<MomentCandidate | null>(null);
  readonly previewError = signal('');
  readonly error = signal('');
  readonly selected = computed(() => {
    let remaining = this.data().duration;
    const result: MomentCandidate[] = [];
    for (const id of this.ids()) {
      const candidate = this.data().candidates.find((c) => c.id === id);
      if (!candidate || remaining <= 0.001) break;
      const seconds = Math.min(candidate.end - candidate.start, remaining);
      result.push({ ...candidate, end: candidate.start + seconds });
      remaining -= seconds;
    }
    return result;
  });
  readonly seconds = computed(() => this.selected().reduce((sum, c) => sum + c.end - c.start, 0));
  readonly available = computed(() =>
    this.data().candidates.filter((c) => !this.ids().includes(c.id)),
  );

  constructor() {
    effect(() => {
      const data = this.data();
      this.setIds(data.selectedIds);
      this.prompt.set(data.prompt);
      this.preview.set(null);
      this.replacement.set(null);
      this.error.set('');
    });
  }

  move(index: number, delta: number): void {
    const ids = [...this.ids()];
    const to = index + delta;
    if (to < 0 || to >= ids.length || this.busy()) return;
    [ids[index], ids[to]] = [ids[to], ids[index]];
    this.setIds(ids);
  }

  remove(id: string): void {
    this.ids.update((ids) => ids.filter((item) => item !== id));
    this.replacement.set(null);
    this.preview.set(null);
    this.error.set('');
  }

  add(candidate: MomentCandidate): void {
    const replace = this.replacement();
    const ids = this.ids().filter((id) => id !== replace);
    const others = this.data().candidates.filter((c) => ids.includes(c.id));
    if (
      others.some(
        (c) =>
          c.filename === candidate.filename &&
          candidate.start < c.end - 0.001 &&
          candidate.end > c.start + 0.001,
      )
    ) {
      this.error.set(
        'Este momento sobrepõe-se a outro da seleção. Remove ou substitui esse momento.',
      );
      return;
    }
    if (!replace && this.seconds() >= this.data().duration - 0.001) {
      this.error.set(
        'A duração pretendida já está preenchida. Substitui ou remove um momento para adicionar outro.',
      );
      return;
    }
    const updated = replace
      ? this.ids().map((id) => (id === replace ? candidate.id : id))
      : [...ids, candidate.id];
    // Drop fully unused trailing candidates; keep the last partially trimmed moment visible.
    this.setIds(updated);
    this.replacement.set(null);
    this.preview.set(null);
    this.error.set('');
  }

  private setIds(updated: string[]): void {
    let left = this.data().duration;
    this.ids.set(
      updated.filter((id) => {
        const c = this.data().candidates.find((item) => item.id === id)!;
        if (left <= 0.001) return false;
        left -= c.end - c.start;
        return true;
      }),
    );
  }

  restore(): void {
    this.setIds(this.data().suggestedIds);
    this.replacement.set(null);
    this.error.set('');
    this.preview.set(null);
  }

  show(candidate: MomentCandidate): void {
    this.preview.set(candidate);
    this.previewError.set('');
  }

  limitPlayback(video: HTMLVideoElement): void {
    const c = this.preview();
    if (c && video.currentTime >= c.end - c.start) video.pause();
  }

  export(): void {
    if (!this.selected().length || this.busy()) return;
    this.exportRequested.emit({
      selectedIds: this.selected().map((c) => c.id),
      duration: this.data().duration,
      enhanceColors: this.data().enhanceColors,
    });
  }
}
