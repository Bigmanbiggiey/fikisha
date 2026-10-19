import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/Button';
import { getOneShotGeo } from '@/features/jobs/geo';

import { PILOT_CENTRE, tileLayer, type LatLng } from './mapConfig';
import { pinIcon } from './pinIcon';

export interface LeafletPickerProps {
  value: LatLng | null;
  onChange: (p: LatLng) => void;
  /** tiles could not load (offline, provider down): fall back to typing */
  onUnavailable: () => void;
  label: string;
}

/**
 * The map itself (loaded on demand: only screens with a map pay for Leaflet).
 * Tap or click to place the pin, drag it to adjust, or use the buttons:
 * "Use my location" (asks the browser each time) and "Pin the map centre"
 * (the keyboard route: focus the map, pan with the arrow keys, then pin).
 */
export default function LeafletPicker({ value, onChange, onUnavailable, label }: LeafletPickerProps): JSX.Element {
  const { t } = useTranslation('common');
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const marker = useRef<L.Marker | null>(null);
  const change = useRef(onChange);
  change.current = onChange;
  const unavailable = useRef(onUnavailable);
  unavailable.current = onUnavailable;
  const [locating, setLocating] = useState(false);
  const [locateFailed, setLocateFailed] = useState(false);

  useEffect(() => {
    const tiles = tileLayer();
    if (!el.current || !tiles) return;
    const m = L.map(el.current, {
      center: value ?? PILOT_CENTRE,
      zoom: value ? 17 : 13,
      keyboard: true,
    });
    let loaded = 0;
    let failed = 0;
    L.tileLayer(tiles.url, { attribution: tiles.attribution, maxZoom: 19 })
      .on('tileload', () => {
        loaded += 1;
      })
      .on('tileerror', () => {
        failed += 1;
        if (failed >= 4 && loaded === 0) unavailable.current();
      })
      .addTo(m);
    m.on('click', (e: L.LeafletMouseEvent) => change.current({ lat: e.latlng.lat, lng: e.latlng.lng }));
    map.current = m;
    return () => {
      m.remove();
      map.current = null;
      marker.current = null;
    };
    // The map is created once; `value` changes move the marker below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    if (!value) {
      marker.current?.remove();
      marker.current = null;
      return;
    }
    if (!marker.current) {
      marker.current = L.marker(value, { draggable: true, icon: pinIcon('brand'), keyboard: false })
        .on('dragend', (e) => {
          const p = (e.target as L.Marker).getLatLng();
          change.current({ lat: p.lat, lng: p.lng });
        })
        .addTo(m);
    } else {
      marker.current.setLatLng(value);
    }
  }, [value]);

  async function locateMe(): Promise<void> {
    setLocating(true);
    setLocateFailed(false);
    const geo = await getOneShotGeo();
    setLocating(false);
    if (!geo || geo.lat == null || geo.lng == null) {
      setLocateFailed(true);
      return;
    }
    const p = { lat: geo.lat, lng: geo.lng };
    change.current(p);
    map.current?.setView(p, 17);
  }

  function pinCentre(): void {
    const c = map.current?.getCenter();
    if (c) change.current({ lat: c.lat, lng: c.lng });
  }

  return (
    <div className="space-y-2">
      <div
        ref={el}
        role="application"
        aria-label={label}
        className="h-64 w-full overflow-hidden rounded-md border border-line-strong md:h-80"
      />
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" loading={locating} onClick={() => void locateMe()}>
          {t('map.useMyLocation')}
        </Button>
        <Button type="button" variant="ghost" onClick={pinCentre}>
          {t('map.pinCentre')}
        </Button>
      </div>
      {locateFailed && <p className="text-body-sm text-fg-muted">{t('map.locateFailed')}</p>}
    </div>
  );
}
