import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class CursorService {
  
  cursorList = Array.from({ length: 12 }, (_, i) => `/assets/cursors/cursor${i + 1}.png`);
  
  PLAYER_COLORS = [
    "#e6194b", "#3cb44b", "#ffe119", "#437fd8",
    "#f58231", "#440568", "#46f0f0", "#f032e6",
    "#1d0a0a", "#fabebe", "#008080", "#2600ff"
  ]
  
  cursorMap: Record<string, string> = {};

  constructor() {
    // Build map: color → cursor path
    this.PLAYER_COLORS.forEach((color, index) => {
      this.cursorMap[color] = this.cursorList[index];
    });

    // Restore cursor if exists in sessionStorage
    const savedColor = sessionStorage.getItem('cursorColor');
    if (savedColor) {
      this.applyGlobalCursor(savedColor, false); // false = don't save again
    }
  }

  applyGlobalCursor(color: string, save: boolean = true) {
    const cursor = this.cursorMap[color];
    if (!cursor) return;

    document.documentElement.style.cursor = `url(${cursor}), auto`;

    // Save to sessionStorage instead of localStorage
    if (save) {
      sessionStorage.setItem('cursorColor', color);
    }
  }

  resetCursor() {
    document.documentElement.style.cursor = 'auto';
    sessionStorage.removeItem('cursorColor');
  }
}
