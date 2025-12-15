import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { WebSocket } from '../../services/web-socket';
import { ApiService } from '../../services/api.service';
import { CursorService } from '../../services/cursor.service';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class Login {
  name = '';
  constructor(private router: Router, private ws: WebSocket, private api: ApiService, private cursorService: CursorService) { }

login() {
  if (!this.name.trim()) return;



  // Call REST login first
   this.api.login(this.name).subscribe(res => {

    sessionStorage.setItem('playerName', res.userName);
    sessionStorage.setItem('playerId', res.userId);
    sessionStorage.setItem('playerColor', res.color); 
     this.ws.connect(this.name);
     this.router.navigate(['/menu']);
    //  this.cursorService.applyGlobalCursor(res.color);
    });
}
}
