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
}