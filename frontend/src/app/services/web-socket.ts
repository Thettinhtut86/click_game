import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class WebSocket {

  private socket!: WebSocketSubject<any>;
  private isConnected = false;

  private userName!: string;
  private userId!: string;
  public currentGameState: any = null;
  // SINGLE STREAM
  public messages$ = new Subject<any>();

  connect(userName: string, userId?: string) {

    if (this.socket && !this.socket.closed) {return;}

    this.userName = userName;
    this.userId = userId || '';

    this.socket = webSocket({

      url: `ws://192.168.250.1:8000/ws/${userName}`,

      serializer: (msg: any) => JSON.stringify(msg),

      deserializer: ({ data }) => JSON.parse(data),

      openObserver: {
        next: () => {
          console.log('WS CONNECTED');
          this.isConnected = true;
        }
      },

      closeObserver: {
        next: () => {
          console.log('WS CLOSED');
          this.isConnected = false;
        }
      }

    });

    this.socket.subscribe({
      next: (msg) => {
        if (msg.action === 'game_started') {
          this.currentGameState = msg;
  }
        this.messages$.next(msg);
      },

    error: (err) => {

      console.error('WS ERROR', err);
      this.isConnected = false;

      setTimeout(() => {
        console.log('Reconnecting WS...');
        this.connect(this.userName, this.userId);
      }, 2000);
    },

      complete: () => {
        this.isConnected = false;
      }
    });

    this.isConnected = true;

    setTimeout(() => {
      this.send({
        action: 'handshake',
        userName
      });
    }, 100);
  }

send(data: any) {
  if (!this.isConnected || !this.socket) {
    console.warn("WS not ready, dropping:", data);
    return;
  }
  this.socket.next(data);
}

  disconnect() {
    this.isConnected = false;
    this.socket?.complete();
  }

  createRoom(roomId: string, option: 'asc' | 'desc' = 'asc') {
    this.send({
      action: 'create_room',
      roomId,
      option
    });
  }

  joinRoom(roomId: string) {
    this.send({
      action: 'join_room',
      roomId
    });
  }

  leaveRoom(roomId: string) {
    this.send({
      action: 'leave_room',
      roomId
    });
  }

  startGame(roomId: string) {
    this.send({
      action: 'start_game',
      roomId
    });
  }

  selectBubble(roomId: string, bubbleId: string) {
    this.send({
      action: 'select_bubble',
      roomId,
      bubble_id: bubbleId
    });
  }
}