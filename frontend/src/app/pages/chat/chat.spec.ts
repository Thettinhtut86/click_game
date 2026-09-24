import { Subject } from 'rxjs';
import { Chat } from './chat';

describe('Chat', () => {
  let component: Chat;
  let messages$: Subject<any>;
  let ws: any;
  let router: any;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('playerId', '1');
    sessionStorage.setItem('playerName', 'Alice');
    messages$ = new Subject<any>();
    ws = { messages$, send: jasmine.createSpy('send') };
    router = { navigate: jasmine.createSpy('navigate') };
    component = new Chat(ws, router);
    component.ngOnInit();
  });

  afterEach(() => sessionStorage.clear());

  it('loads chat history and normalizes message ids', () => {
    expect(ws.send).toHaveBeenCalledWith({ action: 'load_chat' });

    messages$.next({
      action: 'init_chat',
      messages: [{ id: 1, uid: 2, text: 'hello' }],
    });

    expect(component.messages[0].uid).toBe('2');
  });

  it('sends a non-empty message and clears the input', () => {
    component.chatText = ' hello ';
    component.sendMessage();

    expect(ws.send).toHaveBeenCalledWith({
      action: 'send_message',
      text: ' hello ',
    });
    expect(component.chatText).toBe('');
  });

  it('ignores an empty message', () => {
    component.chatText = '   ';
    component.sendMessage();

    expect(ws.send).toHaveBeenCalledTimes(1);
    expect(ws.send).toHaveBeenCalledWith({ action: 'load_chat' });
  });

  it('tracks typing users and message deletion/restoration', () => {
    messages$.next({ action: 'new_message', message: { id: 10, uid: 2, text: 'hi' } });
    messages$.next({ action: 'typing_start', uid: 2, name: 'Bob' });
    messages$.next({ action: 'message_deleted', message_id: 10 });

    expect(component.typingUsers).toEqual(['Bob']);
    expect(component.messages[0].deleted).toBe(1);

    messages$.next({ action: 'message_restored', message_id: 10 });
    expect(component.messages[0].deleted).toBe(0);
  });

  it('filters messages belonging to the current user', () => {
    component.messages = [
      { id: 1, uid: '1' },
      { id: 2, uid: '2' },
    ];
    component.showOnlyMyMessages = true;

    expect(component.filteredMessages).toEqual([{ id: 1, uid: '1' }]);
  });
});
