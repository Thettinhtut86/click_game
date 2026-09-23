import { Subject } from 'rxjs';
import { CreateRoom } from './create-room';

describe('CreateRoom', () => {
  let component: CreateRoom;
  let messages$: Subject<any>;
  let ws: any;
  let router: any;

  beforeEach(() => {
    sessionStorage.clear();
    messages$ = new Subject<any>();
    ws = { messages$, createRoom: jasmine.createSpy('createRoom') };
    router = { navigate: jasmine.createSpy('navigate') };
    component = new CreateRoom(router, ws);
    component.ngOnInit();
  });

  afterEach(() => component.ngOnDestroy());

  it('starts room creation only once while creating', () => {
    component.createRoom();
    component.createRoom();

    expect(ws.createRoom).toHaveBeenCalledTimes(1);
    expect(ws.createRoom).toHaveBeenCalledWith('asc');
    expect(component.creating).toBeTrue();
  });

  it('stores room information and navigates after creation', () => {
    component.option = 'desc';
    component.createRoom();

    messages$.next({ action: 'room_created', roomId: 5, hostId: '1' });

    expect(component.creating).toBeFalse();
    expect(sessionStorage.getItem('roomId')).toBe('5');
    expect(sessionStorage.getItem('hostId')).toBe('1');
    expect(sessionStorage.getItem('roomOption')).toBe('desc');
    expect(router.navigate).toHaveBeenCalledWith(['/room', 5]);
  });

  it('returns to the menu', () => {
    component.back();
    expect(router.navigate).toHaveBeenCalledWith(['/menu']);
  });
});
