import { Subject, of } from 'rxjs';
import { Menu } from './menu';

describe('Menu', () => {
  let component: Menu;
  let messages$: Subject<any>;
  let ws: any;
  let router: any;
  let api: any;
  let cursor: any;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('playerId', '1');
    sessionStorage.setItem('playerName', 'Alice');
    sessionStorage.setItem('playerColor', '#e6194b');

    messages$ = new Subject<any>();
    ws = { messages$, disconnect: jasmine.createSpy('disconnect') };
    router = {
      url: '/menu',
      navigate: jasmine.createSpy('navigate'),
    };
    api = { logout: jasmine.createSpy('logout').and.returnValue(of({ ok: true })) };
    cursor = { resetCursor: jasmine.createSpy('resetCursor') };

    component = new Menu(ws, router, api, cursor);
    component.ngOnInit();
  });

  afterEach(() => sessionStorage.clear());

  it('updates users and unread count from websocket messages', () => {
    messages$.next({ action: 'menu_update', users: [{ id: '1' }] });
    messages$.next({ action: 'new_message' });

    expect(component.bubbles).toEqual([{ id: '1' }]);
    expect(component.unreadCount).toBe(1);
  });

  it('wraps keyboard navigation at the menu boundaries', () => {
    component.selectedIndex = 0;
    component.handleKeyboardEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
    expect(component.selectedIndex).toBe(3);

    component.handleKeyboardEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    expect(component.selectedIndex).toBe(0);
  });

  it('navigates to chat and clears unread messages', () => {
    component.unreadCount = 4;
    component.allChat();

    expect(component.unreadCount).toBe(0);
    expect(router.navigate).toHaveBeenCalledWith(['/chat']);
  });
});
