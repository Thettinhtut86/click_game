import { Subject } from 'rxjs';
import { Room } from './room';

describe('Room', () => {
  let component: Room;
  let messages$: Subject<any>;
  let ws: any;
  let router: any;
  let cd: any;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('playerId', '1');
    sessionStorage.setItem('playerName', 'Alice');
    sessionStorage.setItem('roomId', 'room-1');

    messages$ = new Subject<any>();
    ws = { messages$, send: jasmine.createSpy('send') };
    router = { navigate: jasmine.createSpy('navigate') };
    cd = { detectChanges: jasmine.createSpy('detectChanges') };

    component = new Room({ snapshot: { params: { id: 'room-1' } } } as any, router, ws);
  });

  afterEach(() => sessionStorage.clear());

  it('creates successfully', () => {
    expect(component).toBeTruthy();
  });

  it('handles a room closed message by returning to the menu', () => {
    component.ngOnInit();
    messages$.next({ action: 'room_closed', message: 'Closed' });

    expect(router.navigate).toHaveBeenCalledWith(['/join-room']);
    component.ngOnDestroy();
  });
});
