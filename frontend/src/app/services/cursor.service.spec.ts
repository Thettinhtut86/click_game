import { TestBed } from '@angular/core/testing';

import { CursorService } from './cursor.service';

describe('CursorService', () => {
  let service: CursorService;

  beforeEach(() => {
    sessionStorage.clear();
    document.documentElement.style.cursor = '';
    TestBed.configureTestingModule({});
    service = TestBed.inject(CursorService);
  });

  afterEach(() => {
    sessionStorage.clear();
    document.documentElement.style.cursor = '';
  });

  it('builds a cursor mapping for all player colors', () => {
    expect(Object.keys(service.cursorMap).length).toBe(12);
    expect(service.cursorMap[service.PLAYER_COLORS[0]]).toBe('/assets/cursors/cursor1.png');
    expect(service.cursorMap[service.PLAYER_COLORS[11]]).toBe('/assets/cursors/cursor12.png');
  });

  it('applies and persists a valid cursor color', () => {
    const color = service.PLAYER_COLORS[2];

    service.applyGlobalCursor(color);

    expect(document.documentElement.style.cursor).toBe(
      'url(/assets/cursors/cursor3.png), auto',
    );
    expect(sessionStorage.getItem('cursorColor')).toBe(color);
  });

  it('ignores an unknown color', () => {
    service.applyGlobalCursor('#unknown');

    expect(document.documentElement.style.cursor).toBe('');
    expect(sessionStorage.getItem('cursorColor')).toBeNull();
  });

  it('resets the cursor and removes persisted color', () => {
    service.applyGlobalCursor(service.PLAYER_COLORS[0]);
    service.resetCursor();

    expect(document.documentElement.style.cursor).toBe('auto');
    expect(sessionStorage.getItem('cursorColor')).toBeNull();
  });
});
