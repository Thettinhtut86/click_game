import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { WebSocket } from '../../services/web-socket';

@Component({
  selector: 'app-game',
  standalone: false,
  templateUrl: './game.html',
  styleUrls: ['./game.css']
})

export class Game implements OnInit, OnDestroy {
  roomId!: string;
  bubbles: Record<string, any> = {};
  players: any[] = [];
  watchers: any[] = [];
  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;
  color = sessionStorage.getItem("playerColor")!;
  option = sessionStorage.getItem('roomOption') || 'asc';
  playOrder: number[] = [];
  displayOrder: number[] = []; 
  scores: Record<string, number> = {};
  indexInOrder = 0;
  gameStarted = false;

  constructor(private route: ActivatedRoute, private router: Router, private ws: WebSocket) {}

  ngOnInit() {
    this.roomId = this.route.snapshot.params['id'];

    this.ws.messages$.subscribe((messages) => {
      if (!messages.length) return;
      const last = messages[messages.length - 1];

      if (last.action === 'game_started') {
        this.bubbles = last.bubbles || {};
        this.players = (last.players || []).slice(0, 4);
        this.watchers = (last.players || []).slice(4);        
        this.option = last.option;
        this.displayOrder = last.display_order || [];
        this.playOrder = last.play_order || [];
        this.gameStarted = true;
        console.log('Game started with order:', this.displayOrder);
        
        this.scores = {};
        this.players.forEach(p => this.scores[p.id] = 0);

        this.indexInOrder = 0;
      }

      if (last.action === 'update_bubbles') {
        this.bubbles = last.bubbles;

        this.scores = {};
        Object.values(this.bubbles).forEach((b: any) => {
          if (b && b.uid) {
            this.scores[b.uid] = (this.scores[b.uid] || 0) + 1;
            const player = this.players.find(p => p.id === b.uid);
            if (player && !player.color) player.color = b.color;
          }
          });
        const clickedCount = Object.values(this.bubbles).filter(b => b !== null).length;
        this.indexInOrder = clickedCount;
      }

      if (last.action === 'end_game') {
        if (last.is_tie && last.winners && last.winners.length > 1) {
          const winnerNames = last.winners.map((w: any) => w?.name || 'Unknown').join(', ');
          alert(`Game Finished! It's a Tie between: ${winnerNames}`);
        } else {
          const winner = last.winner || last.winners?.[0];
          alert(`Game Finished! Winner: ${winner?.name || 'Unknown'}`);
        }
        this.router.navigate(['/menu']);
      }

      if (last.action === 'room_closed') {
        alert(last.message);
        this.router.navigate(['/menu']);
      }
    });
  }

  bubbleIds(): string[] {
    // Use the shuffled order from backend
    return this.displayOrder.map((n) => 'B' + n);
  }

  selectBubble(id: string) {
    if (this.watchers.some(w => w.id === this.uid)) return;

    if (!this.gameStarted) return;
    if (this.bubbles[id]) return; 

    this.ws.send({
      action: 'select_bubble',
      roomId: this.roomId,
      bubble_id: id,
      uid: this.uid
    });
  }

  bubbleColor(bubbleId: string): string {
    const bubbleData = this.bubbles[bubbleId];
    if (!bubbleData) return '#fdfdfd'; // free bubble

    // bubbleData now contains uid and color from server
    return bubbleData.color || '#999'; // use server-sent color
  }

  bubbleTextColor(bubbleId: string): string {
    const bubbleData = this.bubbles[bubbleId];
    if (!bubbleData) return '#333'; // dark text for free bubble

    // For colored bubbles, use white text for better contrast
    return '#fff';
  }


  quitGame() {
    if (confirm('Are you sure you want to quit this game?')) {
      this.ws.send({
        action: 'quit_room',
        roomId: this.roomId,
        uid: this.uid
      });
      sessionStorage.removeItem('roomId');
      this.router.navigate(['/menu']);
    }
  }

  ngOnDestroy() {}
}