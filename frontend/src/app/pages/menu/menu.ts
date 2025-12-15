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

 bubbles:any[] = [];
  constructor(private ws:WebSocket,private router:Router, private api: ApiService, private cursorService:CursorService){}

  ngOnInit() {
    this.name = sessionStorage.getItem('playerName')!;
    this.color = sessionStorage.getItem('playerColor')!;
    this.ws.messages$.subscribe(msgList=>{
      const last = msgList[msgList.length-1];
      if(last?.action==='menu_update') this.bubbles = last.users;
    });
    // Fetch player ID from backend by name
    this.api.getPlayerByName(this.name).subscribe(res => {
      if(res?.id){
        this.uid = res.id;
        sessionStorage.setItem('playerId', this.uid);


      }
    });
  }

  createRoom() { this.router.navigate(['/create']); }
  joinRoom() { this.router.navigate(['/join']); }
  allChat() { this.router.navigate(['/chat']); }
  logout() {
    const uid = sessionStorage.getItem('playerId')!;
    this.api.logout(uid).subscribe(() => {
        this.ws.disconnect();
        sessionStorage.clear();
        this.cursorService.resetCursor();
        this.router.navigate(['/login']);
      });
  }
}