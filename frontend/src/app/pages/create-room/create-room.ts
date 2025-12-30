import { Component } from '@angular/core';

import { Router } from '@angular/router';
import { WebSocket } from '../../services/web-socket';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-create-room',
  standalone: false,
  templateUrl: './create-room.html',
  styleUrl: './create-room.css'
})
  
  
export class CreateRoom {
  option: 'asc' | 'desc' = 'asc';
  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;


  constructor(private router: Router,private ws: WebSocket, private api: ApiService) {}

  createRoom() {
    const uid = sessionStorage.getItem('playerId')!;
    const name = sessionStorage.getItem('playerName')!;
    this.api.createRoom(uid, name).subscribe(res => {
      const roomId = res.room_id;
      sessionStorage.setItem('roomOption', this.option);
      sessionStorage.setItem('playerId', res.uid || uid);
      this.ws.send({ action: 'create_room', roomId, option: this.option });
      this.router.navigate(['/room', roomId]);
    }); 
  }
  back() { this.router.navigate(['/menu']); }

  onBtnEnter(e: MouseEvent) {
  this.updateBtnShadow(e);
  const el = e.currentTarget as HTMLElement;
  el.classList.add('hovered'); 
}

onBtnMove(e: MouseEvent) {
  this.updateBtnShadow(e);
  this.updateLightPosition(e);
}

resetLight(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement;
  el.classList.remove('hovered'); 
  el.style.removeProperty('--x');
  el.style.removeProperty('--y');
  el.style.setProperty('--shadow-opacity', '0.35'); // reset shadow
  el.style.setProperty('--shadow-spread', '16px');   // reset spread
}

private updateBtnShadow(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement;
  const rect = el.getBoundingClientRect();

  // Cursor relative to button center (-1 → 1)
  const cx = (e.clientX - rect.left - rect.width/2) / (rect.width/2);
  const cy = (e.clientY - rect.top - rect.height/2) / (rect.height/2);

  // Distance from center
  const distance = Math.sqrt(cx*cx + cy*cy); // 0 (center) → ~1.4 (corner)

  // Map distance to shadow opacity (0.35 → 0.7)
  const minOpacity = 0.35;
  const maxOpacity = 0.7;
  const shadowOpacity = minOpacity + (maxOpacity - minOpacity) * distance;

  // Map distance to shadow spread (optional: more spread near edges)
  const minSpread = 16;
  const maxSpread = 35;
  const shadowSpread = minSpread + (maxSpread - minSpread) * distance;

  el.style.setProperty('--shadow-opacity', `${shadowOpacity}`);
  el.style.setProperty('--shadow-spread', `${shadowSpread}px`);
}

private updateLightPosition(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement;
  const rect = el.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  el.style.setProperty('--x', `${x}px`);
  el.style.setProperty('--y', `${y}px`);
  }
}