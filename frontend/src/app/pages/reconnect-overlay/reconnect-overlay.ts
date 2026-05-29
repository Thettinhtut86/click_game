import { Component, Input, SimpleChanges } from '@angular/core';

@Component({
  selector: 'app-reconnect-overlay',
  standalone: false,
  templateUrl: './reconnect-overlay.html',
  styleUrl: './reconnect-overlay.css'
})
export class ReconnectOverlay {
  @Input() connected = false;   // parent sets this to true on reconnection

  showOverlay = true;           // controls visibility
  private timeoutId: any;

  ngOnChanges(changes: SimpleChanges) {
    if (changes['connected'] && this.connected) {
      // after showing green for 0.5s, hide the overlay
      this.timeoutId = setTimeout(() => {
        this.showOverlay = false;
      }, 500);
    }
  }

  ngOnDestroy() {
    clearTimeout(this.timeoutId);
  }
}
