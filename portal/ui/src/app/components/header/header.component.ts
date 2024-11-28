import { Component, EventEmitter, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { SessionStorageService } from '../../services/session-storage-service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [MatToolbarModule, MatIconModule, MatButtonModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.css'
})
export class HeaderComponent {

  @Output()
  public sidenavTrigger = new EventEmitter();

  constructor(private storageService: SessionStorageService) {}

  /**
   * When the Hamburger Menu is clicked, open/close the sidenav.
   */
  triggerSidenav() {
    this.sidenavTrigger.emit();
  }

  /**
   * Get the value from session storage to show a relevant Page Title.
   */
  getPageTitle() {

    let currentPage = this.storageService.getItem("currentPage");
    if (currentPage == null) {
      currentPage = "";
    }

    return currentPage;
  }

}
