import { Component } from '@angular/core';
import { SessionStorageService } from '../../services/session-storage-service';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [],
  templateUrl: './results.component.html',
  styleUrl: './results.component.css'
})
export class ResultsComponent {

  constructor(private storageService: SessionStorageService) {}

  ngOnInit() {
    this.storageService.setItem("currentPage", "Results")
  }

}
