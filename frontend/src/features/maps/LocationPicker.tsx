import { lazy, Suspense, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { PageLoader } from '@/components/PageLoader';

import { inPilotArea, tileLayer, type LatLng } from './mapConfig';

const LeafletPicker = lazy(() => import('./LeafletPicker'));

/**
 * Pick a point on the map (docs/maps-plan.md M-1). When no map can be shown
 * (no provider configured, offline, tiles failing) it says so and calls
 * `onUnavailable`, and the screen accepts a typed address instead (MD-3).
 * A pin outside Kitengela and environs is allowed, with a warning (MD-5).
 */
export function LocationPicker({
  value,
  onChange,
  onAvailabilityChange,
  label,
}: {
  value: LatLng | null;
  onChange: (p: LatLng) => void;
  /** false once the map can't be used: the pin is then not required */
  onAvailabilityChange?: (available: boolean) => void;
  label: string;
}): JSX.Element {
  const { t } = useTranslation('common');
  const [failed, setFailed] = useState(false);
  const configured = tileLayer() !== null;

  if (!configured || failed) {
    return <Alert tone="warning">{t('map.unavailable')}</Alert>;
  }
  return (
    <div className="space-y-2">
      <Suspense fallback={<PageLoader />}>
        <LeafletPicker
          value={value}
          onChange={onChange}
          label={label}
          onUnavailable={() => {
            setFailed(true);
            onAvailabilityChange?.(false);
          }}
        />
      </Suspense>
      {value ? (
        <p className="text-body-sm text-fg-secondary">
          {t('map.pinned', { lat: value.lat.toFixed(5), lng: value.lng.toFixed(5) })}
        </p>
      ) : (
        <p className="text-body-sm text-fg-muted">{t('map.tapToPin')}</p>
      )}
      {value && !inPilotArea(value) && <Alert tone="warning">{t('map.outsideArea')}</Alert>}
    </div>
  );
}
