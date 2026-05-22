import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { WebSocket } from '../../services/web-socket';

@Component({
  selector: 'app-room',
  standalone: false,
  templateUrl: './room.html',
  styleUrl: './room.css'
})
export class Room implements OnInit, OnDestroy {

  roomId!: string;

  players: any[] = [];

  hostId: string | null = null;

  uid = sessionStorage.getItem('playerId')!;
  uname = sessionStorage.getItem('playerName')!;

  private sub!: Subscription;
  private leaving = false;
  private gameStarting = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private ws: WebSocket
  ) {}

  ngOnInit() {

    this.roomId = this.route.snapshot.params['id'];
    this.ws.joinRoom(this.roomId);
      this.sub = this.ws.messages$.subscribe(msg => {
    if (!msg) return;

    // ROOM UPDATE
    if (msg.action === 'room_update' && msg.roomId === this.roomId) {
      this.players = msg.players || [];
      this.hostId = msg.hostId;
    }
    
    console.log("this player:",this.players);

    // GAME START
    if (msg.action === 'game_started' && msg.roomId === this.roomId) {
      this.gameStarting = true;      
      this.router.navigate(['/game', this.roomId]);
    }

    // ROOM CLOSED
    if (msg.action === 'room_closed' && msg.roomId === this.roomId) {
      alert('Room closed');
      this.router.navigate(['/join-room']);
    }
  });
  }

  ngOnDestroy() {

    this.sub?.unsubscribe();
    // PREVENT DOUBLE LEAVE
    if (this.leaving && !this.gameStarting){
      this.ws.leaveRoom(this.roomId);
    }
  }

  startGame() {
    if (!this.hostId || this.uid !== this.hostId) return;
    this.ws.startGame(this.roomId);
  }

  back() {
    this.leaving = true;
    this.ws.leaveRoom(this.roomId);
    this.router.navigate(['/menu']);
  }
}