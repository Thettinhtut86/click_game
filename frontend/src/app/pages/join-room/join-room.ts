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
    // INITIAL LOAD
    this.loadRooms();
    // LIVE WS UPDATES
    this.sub = this.ws.messages$.subscribe(msg => {
      if (!msg) return;
      // FULL ROOM LIST UPDATE
      if (msg.action === 'rooms_update') {
        this.rooms = (msg.rooms || []).filter(
          (r: Room) => r.player_count < 4
        );
        this.loading = false;
      }
      // ROOM CLOSED
      if (msg.action === 'room_closed') {
        this.rooms = this.rooms.filter(
          r => r.id != msg.roomId
        );
      }
    });
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }

  loadRooms() {
    this.loading = true;
    this.api.listRooms().subscribe({
      next: (res: Room[]) => {
        this.rooms = res.filter(
          r => r.player_count < 4
        );
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  join(roomId: number) {

    this.ws.joinRoom(roomId.toString());
    this.router.navigate(['/room', roomId]);
  }

  back() {

    this.router.navigate(['/menu']);
  }
}