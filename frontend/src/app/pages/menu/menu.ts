import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { WebSocket } from '../../services/web-socket';
import { ApiService } from '../../services/api.service';
import { CursorService } from '../../services/cursor.service';

@Component({
  selector: 'app-menu',
  standalone: false,
  templateUrl: './menu.html',
  styleUrl: './menu.css'
})
  
export class Menu implements OnInit {
  uid!: string;
  name!: string;
  color!: string;
  unreadCount = 0;
  bubbles:any[] = [];
  constructor(private ws:WebSocket,private router:Router, private api: ApiService, private cursorService:CursorService){}

  ngOnInit() {
    this.uid = sessionStorage.getItem('playerId') || '';
    this.name = sessionStorage.getItem('playerName')!;
    this.color = sessionStorage.getItem('playerColor')!;
    const token = sessionStorage.getItem('token');

    this.ws.messages$.subscribe((msg: any) => {

    if (!msg) {
      return;
    }

    if (msg.action === 'menu_update') {
      this.bubbles = msg.users;
    }

    if (msg.action === 'new_message') {
      const current = this.router.url;
      if (current !== '/chat') {
        this.unreadCount++;
      }
    }

  });
}

  createRoom() { this.router.navigate(['/create']); }
  joinRoom() { this.router.navigate(['/join']); }
  allChat() {
    this.unreadCount = 0;
    this.router.navigate(['/chat']);
  }
logout() {
  const uid = sessionStorage.getItem('playerId')!;
  console.log("LOGOUT SENDING UID =", uid);

  if (!uid || uid === 'undefined'){
    this.ws.disconnect();
    sessionStorage.clear();
    this.router.navigate(['/login']);
    return;
    }
    
  this.api.logout(uid).subscribe(() => {
    this.ws.disconnect();
    sessionStorage.clear();
    this.cursorService.resetCursor();
    this.router.navigate(['/login']);
  });

 }
}