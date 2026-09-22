import type { GeoBody } from './types';

/**
 * A single lazy `getCurrentPosition()` reading, taken only when called (on
 * tap of an arrival action) — never on page load, never polled
 * (`chain-of-custody.md` §5: exactly one reading per event, event-based
 * location, not continuous GPS). Resolves to `undefined` on denial,
 * timeout, or an unsupported browser — geo is always best-effort and must
 * never block the underlying `[server]` action.
 *
 * The Geolocation API's own `timeout` option only bounds how long it waits
 * to *acquire a position once permission is granted* — it does **not**
 * cover time spent on a pending permission prompt. Found live: with the
 * prompt never answered (e.g. an automated browser context, or a driver
 * who dismisses/ignores it), neither callback ever fires and this hangs
 * forever, blocking the arrival action it's meant to be best-effort for.
 * An explicit outer race guarantees this always settles.
 */
export function getOneShotGeo(): Promise<GeoBody | undefined> {
  if (!('geolocation' in navigator)) return Promise.resolve(undefined);
  const reading = new Promise<GeoBody | undefined>((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy_m: pos.coords.accuracy,
        }),
      () => resolve(undefined),
      { timeout: 5000, maximumAge: 0 },
    );
  });
  const giveUp = new Promise<undefined>((resolve) => setTimeout(() => resolve(undefined), 5000));
  return Promise.race([reading, giveUp]);
}
