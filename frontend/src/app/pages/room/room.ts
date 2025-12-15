import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

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

  constructor(private route: ActivatedRoute, private router: Router, private ws: WebSocket) { }

  ngOnInit() {
    this.roomId = this.route.snapshot.params['id'];

    this.ws.messages$.subscribe(msgs => {
      const last = msgs[msgs.length - 1];
      if (last?.action === 'room_update' && last.roomId === this.roomId) {
        this.players = last.players;
        this.hostId = last.hostId;
      }
      if (last?.action === 'game_started' && last.roomId === this.roomId) {
        this.router.navigate(['/game', this.roomId]);
      }
    });
  }
  ngOnDestroy() {
    this.ws.send({ action: 'leave_room', roomId: this.roomId, uid: this.uid });
  }

  startGame(){
    if(this.uid===this.hostId)
      this.ws.send({action:'start_game',roomId:this.roomId});
  }

  back() { this.router.navigate(['/menu']); }
}