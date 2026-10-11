import { Component, input, output, signal } from '@angular/core';

@Component({
  selector: 'app-video-upload',
  templateUrl: './video-upload.html',
  styleUrl: './video-upload.scss',
})
export class VideoUploadComponent {
  readonly files = input.required<File[]>();
  readonly disabled = input(false);
  readonly filesAdded = output<File[]>();
  readonly fileRemoved = output<number>();
  readonly dragging = signal(false);

  pick(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.files) this.filesAdded.emit(Array.from(target.files));
    target.value = '';
  }

  dragOver(event: DragEvent): void {
    event.preventDefault();
    if (!this.disabled()) this.dragging.set(true);
  }

  drop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    if (!this.disabled() && event.dataTransfer)
      this.filesAdded.emit(Array.from(event.dataTransfer.files));
  }

  size(bytes: number): string {
    return bytes >= 1024 ** 3
      ? `${(bytes / 1024 ** 3).toFixed(2)} GB`
      : `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  }
}
