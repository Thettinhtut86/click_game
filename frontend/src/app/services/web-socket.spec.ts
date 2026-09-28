import { TestBed } from '@angular/core/testing';
import { WebSocket as AppWebSocket } from './web-socket';

describe('WebSocket service', () => {
  let service: AppWebSocket;
  let socket: { next: jasmine.Spy; complete: jasmine.Spy; unsubscribe: jasmine.Spy };

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({});
    service = TestBed.inject(AppWebSocket);

    socket = {
      next: jasmine.createSpy('next'),
      complete: jasmine.createSpy('complete'),
      unsubscribe: jasmine.createSpy('unsubscribe'),
    };

    (service as any).socket = socket;
    (service as any).connected = true;
    (service as any).userId = 'u1';
    (service as any).userName = 'Alice';
  });

  afterEach(() => sessionStorage.clear());

  it('sends data only when connected', () => {
    service.send({ action: 'ping' });
    expect(socket.next).toHaveBeenCalledWith({ action: 'ping' });

    (service as any).connected = false;
    service.send({ action: 'ignored' });
    expect(socket.next).toHaveBeenCalledTimes(1);
  });

  it('creates a room with the current user and selected option', () => {
    service.createRoom('desc');

    expect(socket.next).toHaveBeenCalledWith({
      action: 'create_room',
      option: 'desc',
      userId: 'u1',
      userName: 'Alice',
    });
  });

  it('joins and leaves rooms', () => {
    service.joinRoom('room-1');
    service.leaveRoom('room-1');

    expect(socket.next.calls.allArgs()).toEqual([
      [{ action: 'join_room', roomId: 'room-1' }],
      [{ action: 'leave_room', roomId: 'room-1' }],
    ]);
  });

  it('requests rooms, starts games, and selects bubbles', () => {
    service.requestRooms();
    service.startGame('room-1');
    service.selectBubble('room-1', 'B10');

    expect(socket.next.calls.allArgs()).toEqual([
      [{ action: 'get_rooms' }],
      [{ action: 'start_game', roomId: 'room-1' }],
      [{ action: 'select_bubble', roomId: 'room-1', bubble_id: 'B10' }],
    ]);
  });

  it('disconnects the current socket', () => {
    service.disconnect();

    expect((service as any).connected).toBeFalse();
    expect(socket.complete).toHaveBeenCalled();
  });
});
