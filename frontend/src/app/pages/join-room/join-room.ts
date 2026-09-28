import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
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
    private router: Router,
    private cd: ChangeDetectorRef
  ) {}

  ngOnInit() {

    this.loading = true;
    
    // LIVE WS UPDATES
    this.sub = this.ws.messages$.subscribe(msg => {
      if (!msg) return;
      // FULL ROOM LIST UPDATE
      switch (msg.action) {

        case 'rooms_update':
          this.rooms = [...(msg.rooms || [])]
            .filter((r: any) => Number(r.player_count || 0) < 4);
          this.loading = false;

          queueMicrotask(() => {
            this.cd.detectChanges();
          });
          break;
        

        case 'room_closed':
          this.rooms = this.rooms.filter(r => r.id !== Number(msg.roomId));
          break;

        case 'join_ack':
          sessionStorage.setItem('roomId',msg.roomId.toString());
          this.router.navigate(['/room',msg.roomId]);
          break;

        case 'watcher_joined':
          this.router.navigate(['/room',msg.roomId]);
          break;
        
        case 'room_created':
          this.router.navigate(['/room',msg.roomId]);

          break;

        case 'error':
          alert(msg.message || 'Operation failed');
          break;
      }
    });
    this.ws.requestRooms();
  }

  trackByRoomId(index: number, room: Room) {
    return room.id;
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