import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import { useEffect, useRef } from 'react';

import { tileLayer, type LatLng } from './mapConfig';
import { pinIcon } from './pinIcon';

export interface MapPoint {
  point: LatLng;
  kind: 'pickup' | 'destination';
  /** a one-letter marker (P / D) so the pins differ by more than colour */
  letter: string;
  /** only the area is shared (MD-2): drawn as a ~1 km circle, not a pin */
  approximate: boolean;
}

/** A read-only map of a job's pickup and destination (docs/maps-plan.md M-4). */
export default function LeafletView({ points, label }: { points: MapPoint[]; label: string }): JSX.Element {
  const el = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const tiles = tileLayer();
    if (!el.current || !tiles || points.length === 0) return;
    const m = L.map(el.current, { zoomControl: true, scrollWheelZoom: false });
    L.tileLayer(tiles.url, { attribution: tiles.attribution, maxZoom: 19 }).addTo(m);
    const bounds = L.latLngBounds([]);
    for (const p of points) {
      if (p.approximate) {
        const circle = L.circle(p.point, {
          radius: 1000,
          className: p.kind === 'destination' ? 'fill-status-danger-fg stroke-status-danger-fg' : 'fill-status-info-fg stroke-status-info-fg',
        }).addTo(m);
        bounds.extend(circle.getBounds());
      } else {
        L.marker(p.point, { icon: pinIcon(p.kind, p.letter), keyboard: false }).addTo(m);
        bounds.extend(p.point);
      }
    }
    m.fitBounds(bounds, { padding: [32, 32], maxZoom: 16 });
    return () => {
      m.remove();
    };
  }, [points]);

  return (
    <div
      ref={el}
      role="img"
      aria-label={label}
      className="h-56 w-full overflow-hidden rounded-md border border-line-strong md:h-72"
    />
  );
}
