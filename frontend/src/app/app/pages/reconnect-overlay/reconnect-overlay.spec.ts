import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ReconnectOverlay } from './reconnect-overlay';

describe('ReconnectOverlay', () => {
  let component: ReconnectOverlay;
  let fixture: ComponentFixture<ReconnectOverlay>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ReconnectOverlay]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ReconnectOverlay);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
