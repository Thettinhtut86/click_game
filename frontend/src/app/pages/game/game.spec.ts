import { Subject } from 'rxjs';
import { Game } from './game';

describe('Game', () => {
  let component: Game;
  let messages$: Subject<any>;
  let ws: any;
  let router: any;
  let cd: any;
  let zone: any;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('playerId', '1');
    sessionStorage.setItem('playerName', 'Alice');
    sessionStorage.setItem('playerColor', '#e6194b');
    sessionStorage.setItem('roomId', 'room-1');

    messages$ = new Subject<any>();
    ws = { messages$, send: jasmine.createSpy('send'), currentGameState: null };
    router = { navigate: jasmine.createSpy('navigate') };
    cd = { detectChanges: jasmine.createSpy('detectChanges') };
    zone = { run: (fn: () => void) => fn() };

    component = new Game({} as any, router, ws, cd, zone);
  });

  afterEach(() => sessionStorage.clear());

  it('loads players, watchers, orders, and scores when a game starts', () => {
    component.loadGame({
      action: 'game_started',
      roomId: 'room-1',
      option: 'asc',
      players: [
        { id: '1', name: 'Alice' },
        { id: '2', name: 'Bob' },
        { id: '3', name: 'Carol' },
        { id: '4', name: 'Dave' },
        { id: '5', name: 'Eve' },
      ],
      bubbles: { B1: null, B2: { uid: '2', color: '#3cb44b' } },
      display_order: [2, 1],
      play_order: [1, 2],
    });

    expect(component.gameStarted).toBeTrue();
    expect(component.players.length).toBe(4);
    expect(component.watchers).toEqual([{ id: '5', name: 'Eve' }]);
    expect(component.scores).toEqual({ '1': 0, '2': 0, '3': 0, '4': 0 });
    expect(component.getNextBubble()).toBe(1);
  });

  it('calculates scores from claimed bubbles', () => {
    component.players = [{ id: '1' }, { id: '2' }];
    component.bubbles = {
      B1: { uid: '1', color: '#e6194b' },
      B2: { uid: '1', color: '#e6194b' },
      B3: { uid: '2', color: '#3cb44b' },
    };

    component.updateScores();

    expect(component.scores).toEqual({ '1': 2, '2': 1 });
    expect(component.players[0].color).toBe('#e6194b');
  });

  it('only sends a bubble selection for an available bubble', () => {
    component.gameStarted = true;
    component.bubbles = { B1: null, B2: { uid: '2' } };

    component.selectBubble('B1');
    component.selectBubble('B2');

    expect(ws.send).toHaveBeenCalledTimes(1);
    expect(ws.send).toHaveBeenCalledWith({
      action: 'select_bubble',
      roomId: 'room-1',
      bubble_id: 'B1',
      uid: '1',
    });
  });

  it('does not allow a watcher to select bubbles', () => {
    component.gameStarted = true;
    component.watchers = [{ id: '1' }];
    component.bubbles = { B1: null };

    component.selectBubble('B1');

    expect(ws.send).not.toHaveBeenCalled();
  });

  it('maps display order to bubble ids', () => {
    component.displayOrder = [3, 1, 2];
    expect(component.bubbleIds()).toEqual(['B3', 'B1', 'B2']);
  });
});
