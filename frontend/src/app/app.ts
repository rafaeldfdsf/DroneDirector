import { Component } from '@angular/core';
import { CreateProjectComponent } from './pages/create-project/create-project';

@Component({
  selector: 'app-root',
  imports: [CreateProjectComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
