import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class WebSocket {
  private socket!: WebSocketSubject<any>;
  public messages$ = new BehaviorSubject<any[]>([]);
  private isConnected = false;
  private userId!: string;
  private userName!: string;

  connect( userName: string) {

    this.userName = userName;
    const url = `ws://192.168.250.1:8080/ws/${userName}`;

    this.socket = webSocket({
      url,
      serializer: (data:any)=>JSON.stringify(data),
      deserializer: ({data}) => JSON.parse(data)
    });

    this.socket.subscribe({
      next: (msg:any) => this.handleMessage(msg),
      error: err => { console.error('WS Error:', err); this.isConnected=false; },
      complete: () => { console.log('WS Closed'); this.isConnected=false; }
    });

    this.isConnected = true;

    // Send handshake
    setTimeout(()=>this.send({action:'handshake', userName}), 100);
  }

  private handleMessage(msg: any) {
    // Append to message stream
    const current = Array.isArray(this.messages$.value) ? this.messages$.value : [];
    this.messages$.next([...current, msg]);
  }

  send(message: any) {
    if(!this.isConnected) {
      console.error('WS not connected');
      return;
    }
    this.socket.next(message);
  }

  disconnect() {
    this.isConnected=false;
    if(this.socket) this.socket.complete();
  }

  // Convenience actions
  createRoom(roomId:string, option:'asc'|'desc'='asc') {
    this.send({action:'create_room', roomId, option});
  }

  joinRoom(roomId:string) {
    this.send({action:'join_room', roomId, uid:this.userId, name:this.userName});
  }

  leaveRoom(roomId:string) {
    this.send({action:'leave_room', roomId, uid:this.userId});
  }

  startGame(roomId:string) {
    this.send({action:'start_game', roomId});
  }

  selectBubble(roomId:string, bubbleId:string) {
    this.send({action:'select_bubble', roomId, bubble_id:bubbleId, uid:this.userId});
  }
}