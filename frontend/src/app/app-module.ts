import { NgModule, provideBrowserGlobalErrorListeners } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms'; 

import { AppRoutingModule } from './app-routing-module';
import { App } from './app';
import { Login } from './pages/login/login';
import { Menu } from './pages/menu/menu';
import { CreateRoom } from './pages/create-room/create-room';
import { JoinRoom } from './pages/join-room/join-room';
import { Chat } from './pages/chat/chat';
import { Room } from './pages/room/room';
import { Game } from './pages/game/game';
import { HttpClientModule } from '@angular/common/http';
import { ReconnectOverlay } from './pages/reconnect-overlay/reconnect-overlay';


@NgModule({
  declarations: [
    App,
    Login,
    Menu,
    CreateRoom,
    JoinRoom,
    Chat,
    Room,
    Game,
    ReconnectOverlay
  ],
  imports: [
    BrowserModule,
    FormsModule,
    AppRoutingModule,
    HttpClientModule
  ],
  providers: [
    provideBrowserGlobalErrorListeners()
  ],
  bootstrap: [App]
})
export class AppModule { }
