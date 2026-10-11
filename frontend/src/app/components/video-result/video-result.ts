import { Component, input, output } from '@angular/core';
import { ProjectStatus } from '../../models/project.model';

@Component({
  selector: 'app-video-result',
  templateUrl: './video-result.html',
  styleUrl: './video-result.scss',
})
export class VideoResultComponent {
  readonly status = input.required<ProjectStatus>();
  readonly videoUrl = input.required<string>();
  readonly downloadUrl = input.required<string>();
  readonly restart = output<void>();
  readonly reviewRequested = output<void>();
}
