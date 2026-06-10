import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { WebSocket } from '../../services/web-socket';

@Component({
  selector: 'app-create-room',
  standalone: false,
  templateUrl: './create-room.html',
  styleUrl: './create-room.css'
})
export class CreateRoom implements OnInit, OnDestroy {

  option: 'asc' | 'desc' = 'asc';

  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;

  creating = false;

  private sub?: Subscription;

  constructor(
    private router: Router,
    private ws: WebSocket
  ) {}

  ngOnInit(): void {

    this.sub = this.ws.messages$.subscribe(msg => {
      if (!msg) return;
      switch (msg.action) {
        case 'room_created':
          this.creating = false;
          sessionStorage.setItem('roomId', msg.roomId);
          sessionStorage.setItem('hostId', msg.hostId);
          sessionStorage.setItem('roomOption', this.option);
          this.router.navigate(['/room',msg.roomId]);
          break;

        case 'error':
          this.creating = false;
          alert(msg.message);
          break;
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  createRoom(): void {
    if (this.creating) return;
    this.creating = true;
    this.ws.createRoom(this.option);
  }

  back(): void {
    this.router.navigate(['/menu']);
  }

  onBtnEnter(e: MouseEvent) {
    this.updateBtnShadow(e);
    const el = e.currentTarget as HTMLElement;
    el.classList.add('hovered');
  }

  onBtnMove(e: MouseEvent) {
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();

    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    el.style.setProperty('--x', `${x}%`);
    el.style.setProperty('--y', `${y}%`);
  }

  resetLight(e: MouseEvent) {
    const el = e.currentTarget as HTMLElement;

    el.classList.remove('hovered');
    el.style.removeProperty('--x');
    el.style.removeProperty('--y');
    el.style.setProperty('--shadow-opacity', '0.35');
    el.style.setProperty('--shadow-spread', '16px');
  }

  private updateBtnShadow(e: MouseEvent) {

    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();

    const cx =
      (e.clientX - rect.left - rect.width / 2) /
      (rect.width / 2);

    const cy =
      (e.clientY - rect.top - rect.height / 2) /
      (rect.height / 2);

    const distance = Math.sqrt(cx * cx + cy * cy);

    const minOpacity = 0.35;
    const maxOpacity = 0.7;

    const shadowOpacity =
      minOpacity +
      (maxOpacity - minOpacity) * distance;

    const minSpread = 16;
    const maxSpread = 35;

    const shadowSpread =
      minSpread +
      (maxSpread - minSpread) * distance;

    el.style.setProperty(
      '--shadow-opacity',
      `${shadowOpacity}`
    );

    el.style.setProperty(
      '--shadow-spread',
      `${shadowSpread}px`
    );
  }
}