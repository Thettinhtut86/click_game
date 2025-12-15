import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { Menu } from './pages/menu/menu';
import { CreateRoom } from './pages/create-room/create-room';
import { JoinRoom } from './pages/join-room/join-room';
import { Room } from './pages/room/room';
import { Game } from './pages/game/game';
import { Chat } from './pages/chat/chat';

const routes: Routes = [
{ path: '', component: Login },
{ path: 'menu', component: Menu },
{ path: 'create', component: CreateRoom },
{ path: 'join', component: JoinRoom },
{ path: 'room/:id', component: Room },
{ path: 'game/:id', component: Game },
{ path: 'chat', component: Chat },
{ path: '**', redirectTo: '' }
];
@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
