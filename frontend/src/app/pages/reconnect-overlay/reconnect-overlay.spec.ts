import { SimpleChange } from '@angular/core';
import { ReconnectOverlay } from './reconnect-overlay';

describe('ReconnectOverlay', () => {
  let component: ReconnectOverlay;

  beforeEach(() => {
    jasmine.clock().install();
    component = new ReconnectOverlay();
  });

  afterEach(() => jasmine.clock().uninstall());

  it('hides the overlay after a successful reconnection', () => {
    component.connected = true;
    component.ngOnChanges({
      connected: new SimpleChange(false, true, false),
    });

    expect(component.showOverlay).toBeTrue();
    jasmine.clock().tick(500);
    expect(component.showOverlay).toBeFalse();
  });

  it('cleans up its timeout', () => {
    component.connected = true;
    component.ngOnChanges({
      connected: new SimpleChange(false, true, false),
    });

    component.ngOnDestroy();
    jasmine.clock().tick(500);

    expect(component.showOverlay).toBeTrue();
  });
});
