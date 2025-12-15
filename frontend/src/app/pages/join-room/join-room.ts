import { Component, OnInit } from '@angular/core';

import { Router } from '@angular/router';
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

export class JoinRoom implements OnInit {
  rooms: any[] = [];
  loading = true;
  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;

  constructor(private ws: WebSocket, private api: ApiService, private router: Router) {}

  ngOnInit() {
    setInterval(() => this.loadRooms(), 5000);
  }

  loadRooms() {
    this.loading = true;
    this.api.listRooms().subscribe({
      next: (res: Room[]) => {
        this.rooms = res.filter(r => r.player_count < 4);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }
  join(roomId: number) {
    this.ws.send({ action: 'join_room', roomId, uid: this.uid, name: this.name });
    this.router.navigate(['/room', roomId]);
  }
   back() { this.router.navigate(['/menu']); }
}