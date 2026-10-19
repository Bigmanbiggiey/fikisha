/**
 * Map configuration (docs/maps-plan.md, MD-1). The tile provider is
 * configuration, not code: production sets `VITE_MAP_TILE_URL` (MapTiler, with
 * its key) and `VITE_MAP_ATTRIBUTION`; switching to another provider is an env
 * change. In local dev only, with nothing set, OpenStreetMap's public tiles
 * are used: their usage policy rules them out for production.
 */

export interface LatLng {
  lat: number;
  lng: number;
}

const OSM_DEV_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '© OpenStreetMap contributors';

export function tileLayer(): { url: string; attribution: string } | null {
  const url = import.meta.env.VITE_MAP_TILE_URL;
  if (url) return { url, attribution: import.meta.env.VITE_MAP_ATTRIBUTION || OSM_ATTRIBUTION };
  if (import.meta.env.DEV) return { url: OSM_DEV_TILES, attribution: OSM_ATTRIBUTION };
  return null; // no provider configured: screens fall back to typed addresses (MD-3)
}

/** Whether a map can be offered at all (a provider is configured). */
export function mapConfigured(): boolean {
  return tileLayer() !== null;
}

/** Kitengela town centre: where a new map opens. */
export const PILOT_CENTRE: LatLng = { lat: -1.4775, lng: 36.9601 };

/** Kitengela and environs (Isinya, Kisaju, Athi River, Kajiado-north). A pin
 * outside is allowed, with a warning (MD-5). */
const PILOT_AREA = { south: -2.0, north: -1.2, west: 36.6, east: 37.25 };

export function inPilotArea(p: LatLng): boolean {
  return (
    p.lat >= PILOT_AREA.south && p.lat <= PILOT_AREA.north && p.lng >= PILOT_AREA.west && p.lng <= PILOT_AREA.east
  );
}

/** Coordinates as the API takes them: decimal strings, 6 places. */
export function toApi(p: LatLng): { lat: string; lng: string } {
  return { lat: p.lat.toFixed(6), lng: p.lng.toFixed(6) };
}

/** A location's coordinates as numbers, or null when it has no pin. */
export function fromApi(loc: { lat?: string | number | null; lng?: string | number | null } | null | undefined): LatLng | null {
  if (!loc || loc.lat === null || loc.lat === undefined || loc.lng === null || loc.lng === undefined) return null;
  const lat = Number(loc.lat);
  const lng = Number(loc.lng);
  return Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
}

/** "Open in Google Maps" (MD-6): directions to the point in the phone's own
 * maps app. Only built when the operator taps it; carries just the point. */
export function googleMapsDirectionsUrl(p: LatLng): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${p.lat.toFixed(6)},${p.lng.toFixed(6)}`;
}
