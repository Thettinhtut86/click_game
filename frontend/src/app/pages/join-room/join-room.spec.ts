import { Subject } from 'rxjs';
import { JoinRoom } from './join-room';

describe('JoinRoom', () => {
  let component: JoinRoom;
  let messages$: Subject<any>;
  let ws: any;
  let router: any;
  let cd: any;

  beforeEach(() => {
    sessionStorage.clear();
    messages$ = new Subject<any>();
    ws = {
      messages$,
      requestRooms: jasmine.createSpy('requestRooms'),
      joinRoom: jasmine.createSpy('joinRoom'),
    };
    router = { navigate: jasmine.createSpy('navigate') };
    cd = { detectChanges: jasmine.createSpy('detectChanges') };
    component = new JoinRoom(ws, router, cd);
    component.ngOnInit();
  });

  afterEach(() => component.ngOnDestroy());

  it('requests rooms on initialization', () => {
    expect(ws.requestRooms).toHaveBeenCalled();
  });

  it('keeps only rooms with fewer than four players', async () => {
    messages$.next({
      action: 'rooms_update',
      rooms: [
        { id: 1, player_count: 0 },
        { id: 2, player_count: 3 },
        { id: 3, player_count: 4 },
      ],
    });

    expect(component.rooms.map(r => r.id)).toEqual([1, 2]);
    expect(component.loading).toBeFalse();
  });

  it('joins a selected room', () => {
    component.join(7);
    expect(ws.joinRoom).toHaveBeenCalledWith('7');
  });

  it('navigates after a successful join', () => {
    messages$.next({ action: 'join_ack', roomId: 7 });

    expect(sessionStorage.getItem('roomId')).toBe('7');
    expect(router.navigate).toHaveBeenCalledWith(['/room', 7]);
  });
});
