import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { WebSocket } from '../../services/web-socket';
import { ApiService } from '../../services/api.service';

interface Room {
  id: number;
  host_id: string;
  host_name: string;
  created_at: string;
  player_count: number;
}

@Component({
  selector: 'app-join-room',
  standalone: false,
  templateUrl: './join-room.html',
  styleUrl: './join-room.css'
})
export class JoinRoom implements OnInit, OnDestroy {

  rooms: Room[] = [];

  loading = true;

  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;

  private sub!: Subscription;

  constructor(
    private ws: WebSocket,
    private api: ApiService,
    private router: Router
  ) {}

  ngOnInit() {

    this.loading = true;

    this.ws.requestRooms();
    // LIVE WS UPDATES
    this.sub = this.ws.messages$.subscribe(msg => {
      if (!msg) return;
      // FULL ROOM LIST UPDATE
      switch (msg.action) {

        case 'rooms_update':
          this.rooms = (msg.rooms || [])
            .filter((r: Room) => r.player_count < 4);
          this.loading = false;
          break;

        case 'room_closed':
          this.rooms = this.rooms.filter(r => r.id !== Number(msg.roomId));
          break;

        case 'join_ack':
          this.router.navigate(['/room',msg.roomId]);
          break;

        case 'watcher_joined':
          this.router.navigate(['/room',msg.roomId]);
          break;

        case 'error':
          alert(msg.message || 'Operation failed');
          break;
      }
    });
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }

  join(roomId: number) {

    this.ws.joinRoom(roomId.toString());
  }

  back() {

    this.router.navigate(['/menu']);
  }
}