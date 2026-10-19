import { lazy, Suspense, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { PageLoader } from '@/components/PageLoader';

import type { MapPoint } from './LeafletView';
import { fromApi, googleMapsDirectionsUrl, tileLayer } from './mapConfig';

const LeafletView = lazy(() => import('./LeafletView'));

interface LocationLike {
  lat?: string | number | null;
  lng?: string | number | null;
  geo_state?: string;
}

/**
 * A job's pickup and destination on a map, with "Open in Google Maps" for
 * each exact point (docs/maps-plan.md M-4, MD-6). Where only the area is
 * shared with this viewer (MD-2: an operator not assigned the job), it shows
 * the area and no directions. Renders nothing when neither point is pinned.
 */
export function JobMap({
  pickup,
  destination,
}: {
  pickup: LocationLike | null | undefined;
  destination: LocationLike | null | undefined;
}): JSX.Element | null {
  const { t } = useTranslation('common');
  const points = useMemo(() => {
    const out: MapPoint[] = [];
    const p = fromApi(pickup);
    const d = fromApi(destination);
    if (p) out.push({ point: p, kind: 'pickup', letter: 'P', approximate: pickup?.geo_state === 'COARSENED' });
    if (d) out.push({ point: d, kind: 'destination', letter: 'D', approximate: destination?.geo_state === 'COARSENED' });
    return out;
  }, [pickup, destination]);

  if (points.length === 0) return null;
  const approximate = points.some((p) => p.approximate);
  return (
    <section aria-labelledby="job-map-heading" className="space-y-2">
      <h2 id="job-map-heading" className="text-label text-fg-secondary">
        {t('map.jobMapTitle')}
      </h2>
      {tileLayer() && (
        <Suspense fallback={<PageLoader />}>
          <LeafletView points={points} label={t('map.jobMapLabel')} />
        </Suspense>
      )}
      <ul className="flex flex-wrap gap-2 text-body-sm">
        {points.map((p) => (
          <li key={p.kind} className="flex items-center gap-2">
            <span className="font-semibold text-fg">
              {p.letter} · {t(`map.${p.kind}`)}
            </span>
            {!p.approximate && (
              <a
                href={googleMapsDirectionsUrl(p.point)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-target items-center rounded-md border border-line-strong px-3 font-medium text-action-secondary-text"
              >
                {t('map.openInGoogleMaps')}
              </a>
            )}
          </li>
        ))}
      </ul>
      {approximate && <p className="text-body-sm text-fg-muted">{t('map.approximateNote')}</p>}
    </section>
  );
}
