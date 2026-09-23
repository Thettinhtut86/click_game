import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ApiService } from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('posts the player name to login', () => {
    service.login(' Alice ').subscribe();

    const request = http.expectOne('http://192.168.250.3:8000/login');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ user_name: ' Alice ' });
    request.flush({ user_id: '1', userName: 'Alice', color: '#fff', token: 'token' });
  });

  it('posts the player id to logout', () => {
    service.logout('123').subscribe();

    const request = http.expectOne('http://192.168.250.3:8000/logout');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ user_id: '123' });
    request.flush({ ok: true });
  });

  it('gets the room list', () => {
    service.listRooms().subscribe();

    const request = http.expectOne('http://192.168.250.3:8000/rooms');
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });
});
