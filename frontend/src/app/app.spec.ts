import { Subject } from 'rxjs';
import { App } from './app';

import { NavigationEnd } from '@angular/router';

describe('App', () => {
  it('tracks websocket connection state', () => {
    const states$ = new Subject<any>();
    const ws: any = { connectionState$: states$ };
    const router: any = {
      events: new Subject<any>(),
      routerState: { root: { firstChild: { snapshot: { data: {} } } } },
    };

    const component = new App(ws, router);
    component.ngOnInit();

    states$.next('connected');
    expect(component.state).toBe('connected');

    states$.next('disconnected');
    expect(component.state).toBe('disconnected');
  });

  it('shows the reconnect overlay on non-login routes', () => {
    const states$ = new Subject<any>();
    const events$ = new Subject<any>();
    const ws: any = { connectionState$: states$ };
    const router: any = {
      events: events$,
      routerState: {
        root: { firstChild: { snapshot: { data: { hideOverlay: false } } } },
      },
    };

    const component = new App(ws, router);
    component.ngOnInit();
    events$.next(new NavigationEnd(1, '/menu', '/menu'));

    expect(component.isLoginPage).toBeFalse();
  });
});
