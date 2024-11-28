import { Component } from '@angular/core';
import { SessionStorageService } from '../../services/session-storage-service';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [],
  templateUrl: './not-found.component.html',
  styleUrl: './not-found.component.css'
})
export class NotFoundComponent {

  constructor(private storageService: SessionStorageService) {}

  ngOnInit() {
    this.storageService.setItem("currentPage", "Page Not Found")
  }


}
