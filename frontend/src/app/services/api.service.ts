import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = 'http://192.168.250.1:8080';

  constructor(private http: HttpClient) {}

  login(name: string): Observable<any> {
    return this.http.post(`${this.base}/login`, { user_name: name });
  }

  logout(userId: string): Observable<any> {
    return this.http.post(`${this.base}/logout`, { user_id: userId });
  }

  createRoom(userId: string, userName: string): Observable<any> {
    return this.http.post(`${this.base}/rooms/create`, { user_id: userId, user_name: userName });
  }

  listRooms(): Observable<any> {
    return this.http.get(`${this.base}/rooms`);
  }

  getRoom(roomId: string): Observable<any> {
    return this.http.get(`${this.base}/rooms/${roomId}`);
  }

  getPlayerByName(name: string): Observable<any> {
    return this.http.get(`${this.base}/players/${name}`);
  }
}