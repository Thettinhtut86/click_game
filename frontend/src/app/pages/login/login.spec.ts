import { Login } from './login';
import { of } from 'rxjs';

describe('Login', () => {
  let component: Login;
  let router: any;
  let ws: any;
  let api: any;
  let cursor: any;

  beforeEach(() => {
    router = { navigate: jasmine.createSpy('navigate') };
    ws = { connect: jasmine.createSpy('connect') };
    api = { login: jasmine.createSpy('login').and.returnValue(of({
      userName: 'Alice', user_id: '1', color: '#e6194b', token: 'jwt',
    })) };
    cursor = { applyGlobalCursor: jasmine.createSpy('applyGlobalCursor') };
    sessionStorage.clear();
    component = new Login(router, ws, api, cursor);
  });

  it('does nothing for a blank name', () => {
    component.name = '   ';
    component.login();

    expect(api.login).not.toHaveBeenCalled();
    expect(ws.connect).not.toHaveBeenCalled();
  });

  it('stores login data, connects the websocket, and navigates', () => {
    component.name = 'Alice';
    component.login();

    expect(api.login).toHaveBeenCalledWith('Alice');
    expect(sessionStorage.getItem('playerName')).toBe('Alice');
    expect(sessionStorage.getItem('playerId')).toBe('1');
    expect(sessionStorage.getItem('playerColor')).toBe('#e6194b');
    expect(sessionStorage.getItem('token')).toBe('jwt');
    expect(ws.connect).toHaveBeenCalledWith('Alice', 'jwt', '1');
    expect(router.navigate).toHaveBeenCalledWith(['/menu']);
  });
});
