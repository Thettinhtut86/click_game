import { Component } from '@angular/core';
import { WebSocket } from '../../services/web-socket';
import { Router } from '@angular/router';

@Component({
  selector: 'app-chat',
  standalone: false,
  templateUrl: './chat.html',
  styleUrl: './chat.css'
})
export class Chat {
  messages: any[] = [];
  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;
  chatText = '';

  constructor(private ws: WebSocket, private router: Router) { }

  ngOnInit() {
    this.ws.messages$.subscribe((messages) => {
      if (!messages.length) return;

      const last = messages[messages.length - 1]; // take the last message
      if (last.action === 'init') this.messages = last.messages || [];
      if (last.action === 'new_message') this.messages.push(last.message);
    });
  }

  sendMessage() {
    if (!this.chatText.trim()) return;
    this.ws.send({ action: 'send_message', text: this.chatText });
    this.chatText = '';
  }

  back() { this.router.navigate(['/menu']); }

  ngOnDestroy() {
    // Do not close socket here
  }
}