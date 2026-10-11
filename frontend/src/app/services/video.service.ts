import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ProcessOptions, ProjectStatus, ReviewData, ExportOptions } from '../models/project.model';

@Injectable({ providedIn: 'root' })
export class VideoService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000/api/projects';

  createProject(): Observable<{ projectId: string }> {
    return this.http.post<{ projectId: string }>(this.baseUrl, {});
  }

  uploadVideos(projectId: string, files: File[]): Observable<HttpEvent<unknown>> {
    const form = new FormData();
    files.forEach((file) => form.append('videos', file, file.name));
    return this.http.post(`${this.baseUrl}/${projectId}/videos`, form, {
      observe: 'events',
      reportProgress: true,
    });
  }

  process(projectId: string, options: ProcessOptions): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/${projectId}/process`, options);
  }

  getStatus(projectId: string): Observable<ProjectStatus> {
    return this.http.get<ProjectStatus>(`${this.baseUrl}/${projectId}/status`);
  }

  analyze(projectId: string, options: ProcessOptions): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/${projectId}/analyze`, options);
  }

  getReview(projectId: string): Observable<ReviewData> {
    return this.http.get<ReviewData>(`${this.baseUrl}/${projectId}/review`);
  }

  suggest(projectId: string, prompt: string): Observable<ReviewData> {
    return this.http.post<ReviewData>(`${this.baseUrl}/${projectId}/suggest`, { prompt });
  }

  export(projectId: string, options: ExportOptions): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/${projectId}/export`, options);
  }

  mediaUrl(path: string): string {
    return `http://localhost:8000${path}`;
  }

  resultUrl(projectId: string, download = false): string {
    return `${this.baseUrl}/${projectId}/result${download ? '?download=true' : ''}`;
  }
}
