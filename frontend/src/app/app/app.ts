import { Component, signal } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';
import { WebSocket } from './services/web-socket';


@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  standalone: false,
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('click-game');
  state: 'connected' | 'connecting' | 'disconnected' = 'connecting';
  isLoginPage = false;
  
  constructor(private ws: WebSocket, private router: Router) { }
  
  ngOnInit() {
    this.ws.connectionState$.subscribe(s => {
      this.state = s;
    });

    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe(() => {
        const route = this.router.routerState.root.firstChild;

        this.isLoginPage = route?.snapshot.data?.['hideOverlay'] === true;
    });
  }
}
