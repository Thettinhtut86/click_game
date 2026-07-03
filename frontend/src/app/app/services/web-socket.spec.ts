import { TestBed } from '@angular/core/testing';

import { WebSocket } from './web-socket';

describe('WebSocket', () => {
  let service: WebSocket;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(WebSocket);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
