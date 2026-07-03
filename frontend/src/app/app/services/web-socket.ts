import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class WebSocket {

  private socket!: WebSocketSubject<any>;
  private connected  = false;
  private connecting = false;
  private reconnectAttempts = 0;
  private userName!: string;
  private userId!: string;
  private token!: string;
  public currentGameState: any = null;
  // SINGLE STREAM
  public messages$ = new Subject<any>();

  public connectionState$ = new Subject<'connected' | 'connecting' | 'disconnected'>();

  constructor() {
    this.restoreConnection();
  }
  private restoreConnection() {
    const token = sessionStorage.getItem('token');
    const userName = sessionStorage.getItem('playerName');
    const userId = sessionStorage.getItem('playerId');

    // If session data exists, we survived a refresh. Reconnect immediately.
    if (token && userName) {
      this.connect(userName, token, userId || undefined);
    }
  }

  connect(userName: string, token: string, userId?: string) {
    if (this.connected || this.connecting) return;
    
    this.connecting = true;
    this.connected = false;
    this.connectionState$.next('connecting');

    this.userName = userName;
    this.userId = userId || '';
    this.token = token;
    
    if (this.socket) {
      try {
        this.socket.unsubscribe();
      } catch {}
    }

    this.socket = webSocket({

    url: `ws://192.168.250.3:8000/ws?token=${token}`,

      serializer: (msg: any) => JSON.stringify(msg),
      deserializer: ({ data }) => JSON.parse(data),

      openObserver: {
        next: () => {
          console.log('WS CONNECTED');

          this.connected = true;
          this.connecting = false;
          this.reconnectAttempts = 0;
          this.connectionState$.next('connected');
          
          this.send({ action: 'handshake', userName: this.userName });
        }
      },

      closeObserver: {
        next: () => {
          console.log('WS CLOSED');

          this.connected = false;
          this.connecting = false;

          this.connectionState$.next('disconnected');

          this.triggerReconnect();
        }
      }
    });
    this.socket.subscribe({
      next: (msg) => this.messages$.next(msg),

      error: () => {
        this.connected = false;
        this.connecting = false;
        this.connectionState$.next('disconnected');
        this.triggerReconnect();
      },

      complete: () => {
        this.connected = false;
        this.connecting = false;
        this.connectionState$.next('disconnected');
        this.triggerReconnect();
      }
    });

    setTimeout(() => {
      this.send({ action: 'handshake', userName });
    }, 100);
}

send(data: any) {
  if (!this.connected || !this.socket) {
    console.warn("WS not ready, dropping:", data);
    return;
  }
  this.socket.next(data);
}

  disconnect() {
    this.connected  = false;
    this.socket?.complete();
  }

  createRoom(option: 'asc' | 'desc' = 'asc') {
    console.log("userId: ", this.userId);
    console.log("userName: ", this.userName);
    console.log();
    this.send({
      action: 'create_room',
      option,
      userId: this.userId,      
      userName: this.userName
    });
  }

  joinRoom(roomId: string) {
    this.send({
      action: 'join_room',
      roomId
    });
  }

  requestRooms() {
    const msg = { action: 'get_rooms' };
    // console.log("SEND WS:", msg);
    this.send(msg);
  }

  leaveRoom(roomId: string) {
    this.send({
      action: 'leave_room',
      roomId
    });
  }

  startGame(roomId: string) {
    const msg = {
      action: 'start_game',
      roomId
     };
    // console.log("SEND WS:", msg);    
    this.send(msg);
  }

  selectBubble(roomId: string, bubbleId: string) {
    this.send({
      action: 'select_bubble',
      roomId,
      bubble_id: bubbleId
    });
  }
  private triggerReconnect() {

    if (this.reconnectAttempts >= 5) return;

    this.reconnectAttempts++;

    setTimeout(() => {

      const t = sessionStorage.getItem('token');
      const n = sessionStorage.getItem('playerName');
      const id = sessionStorage.getItem('playerId');

      if (t && n) {
        this.connect(n, t, id || undefined);
      }

    }, 1500 * this.reconnectAttempts); 
  }
}