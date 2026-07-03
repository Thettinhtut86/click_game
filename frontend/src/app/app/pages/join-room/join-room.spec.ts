import { ComponentFixture, TestBed } from '@angular/core/testing';

import { JoinRoom } from './join-room';

describe('JoinRoom', () => {
  let component: JoinRoom;
  let fixture: ComponentFixture<JoinRoom>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [JoinRoom]
    })
    .compileComponents();

    fixture = TestBed.createComponent(JoinRoom);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
