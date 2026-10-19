import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { Select } from '@/components/Select';
import { StatusBadge } from '@/components/StatusBadge';
import { LocationPicker } from '@/features/maps/LocationPicker';
import { fromApi, mapConfigured, toApi, type LatLng } from '@/features/maps/mapConfig';
import { localizeError } from '@/services/errorMessage';

import { orgApi } from './orgApi';
import { LOCATION_TYPES, type BusinessLocation } from './types';

/**
 * A business's locations, each pinned on the map and named
 * (docs/maps-plan.md M-2). A new location needs a pin whenever the map can
 * load (MD-3); a location saved before maps existed shows "Add the pin". The
 * pin is what a job's pickup copies, so operators can navigate to it.
 */
export function BusinessLocationsCard({
  businessId,
  locations,
  canManage,
}: {
  businessId: string;
  locations: BusinessLocation[];
  canManage: boolean;
}): JSX.Element {
  const { t } = useTranslation(['org', 'common', 'errors']);
  const qc = useQueryClient();
  const refresh = (): void => void qc.invalidateQueries({ queryKey: ['business', businessId, 'locations'] });

  const [label, setLabel] = useState('');
  const [type, setType] = useState<string>(locations.length === 0 ? 'MAIN' : 'BRANCH');
  const [landmark, setLandmark] = useState('');
  const [pin, setPin] = useState<LatLng | null>(null);
  const [mapUsable, setMapUsable] = useState(mapConfigured());
  const [error, setError] = useState<string | null>(null);
  const [pinning, setPinning] = useState<string | null>(null);
  const [newPin, setNewPin] = useState<LatLng | null>(null);

  const add = useMutation({
    mutationFn: () =>
      orgApi.addLocation(businessId, {
        label: label.trim(),
        type,
        address_text: landmark.trim(),
        ...(pin ? toApi(pin) : {}),
      }),
    onSuccess: () => {
      setLabel('');
      setLandmark('');
      setPin(null);
      setType('BRANCH');
      setError(null);
      refresh();
    },
    onError: (err) => setError(localizeError(err, t)),
  });

  const savePin = useMutation({
    mutationFn: ({ id, p }: { id: string; p: LatLng }) => orgApi.updateLocation(businessId, id, toApi(p)),
    onSuccess: () => {
      setPinning(null);
      setNewPin(null);
      setError(null);
      refresh();
    },
    onError: (err) => setError(localizeError(err, t)),
  });

  const pinMissing = mapUsable && !pin;
  function submit(e: FormEvent): void {
    e.preventDefault();
    if (label.trim() && !pinMissing) add.mutate();
  }

  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('org:business.locations')}</h2>
      <p className="mt-1 text-caption text-fg-muted">{t('org:business.mainLocationNote')}</p>
      <ul className="mt-2 divide-y divide-line text-body-sm">
        {locations.map((l) => {
          const point = fromApi(l);
          return (
            <li key={l.id} className="space-y-2 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  <span className="font-medium text-fg">{l.label}</span>
                  {l.address_text ? <span className="text-fg-muted"> · {l.address_text}</span> : null}
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  <StatusBadge
                    tone={l.type === 'MAIN' ? 'success' : 'neutral'}
                    icon={l.type === 'MAIN' ? 'check' : undefined}
                    label={l.type}
                  />
                  <StatusBadge
                    tone={point ? 'success' : 'warning'}
                    icon={point ? 'pinCheck' : 'pin'}
                    label={point ? t('org:locationMap.pinned') : t('common:map.noPin')}
                  />
                  {canManage && mapConfigured() && (
                    <Button
                      variant="ghost"
                      onClick={() => {
                        setPinning(pinning === l.id ? null : l.id);
                        setNewPin(point);
                      }}
                    >
                      {point ? t('org:locationMap.movePin') : t('org:locationMap.addPin')}
                    </Button>
                  )}
                  {canManage && (
                    <Button
                      variant="destructive"
                      onClick={() =>
                        orgApi
                          .removeLocation(businessId, l.id)
                          .then(refresh)
                          .catch(() => undefined)
                      }
                    >
                      {t('org:common.remove')}
                    </Button>
                  )}
                </span>
              </div>
              {pinning === l.id && (
                <div className="space-y-2 rounded-md bg-surface-sunken p-3">
                  <LocationPicker value={newPin} onChange={setNewPin} label={t('org:locationMap.mapLabel', { name: l.label })} />
                  <Button
                    disabled={!newPin}
                    loading={savePin.isPending}
                    onClick={() => newPin && savePin.mutate({ id: l.id, p: newPin })}
                  >
                    {t('org:locationMap.savePin')}
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {canManage && (
        <form className="mt-4 space-y-3 border-t border-line pt-4" onSubmit={submit}>
          <h3 className="text-h3 text-fg">{t('org:business.addLocation')}</h3>
          <LocationPicker
            value={pin}
            onChange={setPin}
            onAvailabilityChange={setMapUsable}
            label={t('org:locationMap.newMapLabel')}
          />
          <div className="grid gap-3 md:grid-cols-3">
            <Field label={t('org:locationMap.name')} hint={t('org:locationMap.nameHint')} required>
              {(p) => <Input {...p} value={label} onChange={(e) => setLabel(e.target.value)} />}
            </Field>
            <Field label={t('org:business.locationType')}>
              {(p) => (
                <Select {...p} value={type} onChange={(e) => setType(e.target.value)}>
                  {LOCATION_TYPES.map((ty) => (
                    <option key={ty} value={ty}>
                      {ty}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label={t('org:locationMap.landmark')} required={!mapUsable}>
              {(p) => <Input {...p} value={landmark} onChange={(e) => setLandmark(e.target.value)} />}
            </Field>
          </div>
          {pinMissing && label.trim() && <p className="text-body-sm text-fg-muted">{t('org:locationMap.pinFirst')}</p>}
          <Button
            type="submit"
            loading={add.isPending}
            disabled={!label.trim() || pinMissing || (!mapUsable && !landmark.trim())}
          >
            {t('org:locationMap.save')}
          </Button>
        </form>
      )}
      {error && (
        <div className="mt-2">
          <Alert tone="danger">{error}</Alert>
        </div>
      )}
    </Card>
  );
}
