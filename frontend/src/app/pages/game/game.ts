import { ChangeDetectorRef, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { WebSocket } from '../../services/web-socket';

@Component({
  selector: 'app-game',
  standalone: false,
  templateUrl: './game.html',
  styleUrls: ['./game.css']
})
export class Game implements OnInit, OnDestroy {


  bubbles: Record<string, any> = {};
  players: any[] = [];
  watchers: any[] = [];

  uid = sessionStorage.getItem('playerId')!;
  name = sessionStorage.getItem('playerName')!;
  color = sessionStorage.getItem('playerColor')!;
  option = sessionStorage.getItem('roomOption') || 'asc';
  roomId = sessionStorage.getItem('roomId')!;

  playOrder: number[] = [];
  displayOrder: number[] = [];

  scores: Record<string, number> = {};

  gameStarted = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private ws: WebSocket,
    private cd: ChangeDetectorRef,
    private zone: NgZone
  ) {}

  ngOnInit() {
    // this.roomId = this.route.snapshot.params['id'];

    const savedGame = this.ws.currentGameState;
    if (savedGame?.action === 'game_started' && savedGame.roomId === this.roomId) {
      this.loadGame(savedGame);
    }

    this.ws.messages$.subscribe((msg: any) => {
    console.log("msg action:", msg.action);
    if (!msg) return;

    this.zone.run(() => {
      switch (msg.action) {
        
        case 'game_started':
          if (msg.roomId === this.roomId) {
            this.loadGame(msg);
          }          
          break;

        case 'update_bubbles':
          this.bubbles = { ...msg.bubbles }; // IMPORTANT
          this.updateScores();
          break;

        case 'end_game':
          this.handleEndGame(msg);
          break;

        case 'room_closed':
          alert(msg.message);
          this.router.navigate(['/menu']);
          break;
      }

      this.cd.detectChanges(); // FORCE UI REFRESH
    });
  });
  }

  // ---------------------------
  // GAME LOAD
  // ---------------------------
  loadGame(msg: any) {
    this.bubbles = msg.bubbles || {};
    this.players = (msg.players || []).slice(0, 4);
    this.watchers = (msg.players || []).slice(4);

    this.option = msg.option;
    this.displayOrder = msg.display_order || [];
    console.log("displayOrder:", this.displayOrder);
    this.playOrder = msg.play_order || [];

    this.gameStarted = true;
    this.scores = {};

    this.players.forEach(p => (this.scores[p.id] = 0));
  }

  // ---------------------------
  // SCORE UPDATE
  // ---------------------------
  updateScores() {
    this.scores = {};

    Object.values(this.bubbles).forEach((b: any) => {
      if (b?.uid) {
        this.scores[b.uid] = (this.scores[b.uid] || 0) + 1;

        const player = this.players.find(p => p.id === b.uid);
        if (player && !player.color) {
          player.color = b.color;
        }
      }
    });
  }

  // ---------------------------
  // NEXT BUBBLE (FIXED LOGIC)
  // ---------------------------
  getNextBubble(): number | null {
    for (const n of this.playOrder) {
      const id = 'B' + n;
      if (this.bubbles[id] === null) {
        return n;
      }
    }
    return null;
  }

  // ---------------------------
  // CLICK BUBBLE
  // ---------------------------
  selectBubble(id: string) {
    if (this.watchers.some(w => w.id === this.uid)) return;
    if (!this.gameStarted) return;

    // FIXED: safe null check
    if (this.bubbles[id] !== null) return;

    this.ws.send({
      action: 'select_bubble',
      roomId: this.roomId,
      bubble_id: id,
      uid: this.uid
    });
  }

  // ---------------------------
  // UI HELPERS
  // ---------------------------
  bubbleColor(bubbleId: string): string {
    const bubble = this.bubbles[bubbleId];
    if (!bubble) return '#fdfdfd';
    return bubble.color || '#999';
  }

  bubbleTextColor(bubbleId: string): string {
    const bubble = this.bubbles[bubbleId];
    return bubble ? '#fff' : '#333';
  }

  bubbleIds(): string[] {
    return this.displayOrder.map(n => 'B' + n);
  }

  // ---------------------------
  // END GAME
  // ---------------------------
  handleEndGame(msg: any) {
    if (msg.is_tie && msg.winners?.length > 1) {
      const names = msg.winners.map((w: any) => w?.name || 'Unknown').join(', ');
      alert(`Game Finished! It's a Tie between: ${names}`);
    } else {
      const winner = msg.winner || msg.winners?.[0];
      alert(`Game Finished! Winner: ${winner?.name || 'Unknown'}`);
    }

    this.router.navigate(['/menu']);
  }

  // ---------------------------
  // QUIT
  // ---------------------------
  quitGame() {
    if (confirm('Are you sure you want to quit this game?')) {
      this.ws.send({
        action: 'quit_room',
        roomId: this.roomId,
        uid: this.uid
      });

      sessionStorage.removeItem('roomId');
      sessionStorage.removeItem('hostId');
      this.router.navigate(['/menu']);
    }
  }

  ngOnDestroy() {
    // optional cleanup (unsubscribe if you later store subscription)
  }
}