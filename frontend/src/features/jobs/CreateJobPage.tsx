import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { PageLoader } from '@/components/PageLoader';
import { diagnosticsApi } from '@/features/diagnostics/diagnosticsApi';
import { localizeError } from '@/services/errorMessage';

import { jobsApi } from './jobsApi';
import { formatKes, parseKesToMinorUnits } from './money';
import { useActiveBusiness } from './useActiveBusiness';
import type { JobCreateBody } from './types';

/**
 * Combines the wireframes' B-CreateJob (§6.2, 8 steps) and B-ReviewSubmit
 * (§6.3) into one component with local step state, rather than two routes
 * handing a draft object across a navigation. The backend has no
 * incremental "create then patch per step" endpoint — `POST /jobs` takes
 * the complete body in one call (`JobCreateSerializer`) — so there is
 * nothing for intermediate steps to save server-side anyway; the whole
 * form is `[local-ok]` until "Send request", which does two calls in
 * sequence: create (still `DRAFT`), then submit (`DRAFT -> REQUESTED`).
 * A known gap: the wireframe's step 7 ("When") has no backing field in
 * `JobCreateSerializer` at all — Phase 2D's schema has no requested-pickup-
 * time field. Folded into `delivery_requirements` as a note rather than
 * silently dropped or inventing a new backend field.
 */

const TOTAL_STEPS = 8;
const HANDLING_FLAGS = ['FRAGILE', 'KEEP_UPRIGHT'] as const;

interface Draft {
  pickupAddress: string;
  pickupContactPhone: string;
  destinationAddress: string;
  recipientName: string;
  recipientPhone: string;
  cargoDescription: string;
  cargoCategory: string;
  handlingFlags: string[];
  hazardous: boolean;
  estWeightKg: string;
  bulky: boolean;
  dimsL: string;
  dimsW: string;
  dimsH: string;
  declaredValue: string;
  vehicleClassCode: string;
  whenAsap: boolean;
  whenNote: string;
  deliveryRequirements: string;
  proposedPrice: string;
}

const EMPTY_DRAFT: Draft = {
  pickupAddress: '',
  pickupContactPhone: '',
  destinationAddress: '',
  recipientName: '',
  recipientPhone: '',
  cargoDescription: '',
  cargoCategory: '',
  handlingFlags: [],
  hazardous: false,
  estWeightKg: '',
  bulky: false,
  dimsL: '',
  dimsW: '',
  dimsH: '',
  declaredValue: '',
  vehicleClassCode: '',
  whenAsap: true,
  whenNote: '',
  deliveryRequirements: '',
  proposedPrice: '',
};

function buildBody(d: Draft): JobCreateBody {
  const whenLine = d.whenAsap
    ? ''
    : d.whenNote
      ? `Requested time: ${d.whenNote}.`
      : '';
  const deliveryRequirements = [whenLine, d.deliveryRequirements.trim()].filter(Boolean).join(' ');
  return {
    pickup_location: { address_text: d.pickupAddress.trim(), contact_phone: d.pickupContactPhone.trim() },
    destination_location: {
      address_text: d.destinationAddress.trim(),
      contact_name: d.recipientName.trim(),
      contact_phone: d.recipientPhone.trim(),
    },
    cargo: {
      description: d.cargoDescription.trim(),
      category_code: d.cargoCategory.trim(),
      declared_value_kes: parseKesToMinorUnits(d.declaredValue) ?? 1,
      est_weight_kg: d.estWeightKg ? Number(d.estWeightKg) : undefined,
      dims_l_cm: d.bulky && d.dimsL ? Number(d.dimsL) : undefined,
      dims_w_cm: d.bulky && d.dimsW ? Number(d.dimsW) : undefined,
      dims_h_cm: d.bulky && d.dimsH ? Number(d.dimsH) : undefined,
      handling_flags: d.hazardous ? [...d.handlingFlags, 'HAZARDOUS'] : d.handlingFlags,
    },
    vehicle_requirement: d.vehicleClassCode
      ? { required_vehicle_class_codes: [d.vehicleClassCode] }
      : undefined,
    recipient_name: d.recipientName.trim(),
    recipient_phone: d.recipientPhone.trim(),
    delivery_requirements: deliveryRequirements,
    proposed_price_kes: d.proposedPrice ? (parseKesToMinorUnits(d.proposedPrice) ?? undefined) : undefined,
  };
}

function step1Valid(d: Draft): boolean {
  return d.pickupAddress.trim().length > 0;
}
function step2Valid(d: Draft): boolean {
  return d.destinationAddress.trim().length > 0 && d.recipientName.trim().length > 0;
}
function step3Valid(d: Draft): boolean {
  return d.cargoDescription.trim().length > 0;
}
function step5Valid(d: Draft): boolean {
  return parseKesToMinorUnits(d.declaredValue) !== null;
}
const STEP_VALIDATORS: Array<(d: Draft) => boolean> = [
  step1Valid,
  step2Valid,
  step3Valid,
  () => true, // weight/size — optional
  step5Valid,
  () => true, // vehicle — optional
  () => true, // when — always valid
  () => true, // delivery requirements — optional
];

export function CreateJobPage(): JSX.Element {
  const { t } = useTranslation(['jobs', 'errors']);
  const navigate = useNavigate();
  const { loading: businessLoading, businessId } = useActiveBusiness();
  const [step, setStep] = useState(0); // 0..7 form steps, 8 = review
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [sentJobId, setSentJobId] = useState<string | null>(null);

  const vehicleTypes = useQuery({
    queryKey: ['reference', 'vehicleTypes'],
    queryFn: diagnosticsApi.reference,
    retry: false,
  });

  function patch(fields: Partial<Draft>): void {
    setDraft((d) => ({ ...d, ...fields }));
  }

  const isReview = step === TOTAL_STEPS;
  const canAdvance = isReview ? true : STEP_VALIDATORS[step]!(draft);

  async function sendRequest(): Promise<void> {
    if (!businessId || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const key = crypto.randomUUID();
      const job = await jobsApi.create(businessId, buildBody(draft), key);
      await jobsApi.submit(job.id, crypto.randomUUID());
      setSentJobId(job.id);
    } catch (err) {
      setSubmitError(localizeError(err, t));
    } finally {
      setSubmitting(false);
    }
  }

  // Navigating is a side effect — it must not run directly in the render
  // body (calling `navigate()` inline here, instead of in an effect, was a
  // real bug found while testing: it re-triggers on every re-render this
  // component gets before it unmounts, which can spiral into a runaway
  // render loop rather than a single clean redirect).
  useEffect(() => {
    if (sentJobId) navigate(`/jobs/${sentJobId}`, { replace: true });
  }, [sentJobId, navigate]);

  if (sentJobId) return <PageLoader />;
  if (businessLoading) return <PageLoader />;
  if (!businessId) {
    return <Alert tone="warning">{t('jobs:home.noBusinessBody')}</Alert>;
  }

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <div>
        <p className="text-label text-fg-secondary">
          {isReview ? t('jobs:create.reviewTitle') : t('jobs:create.stepOf', { n: step + 1, total: TOTAL_STEPS })}
        </p>
        {!isReview && (
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-sunken">
            <div
              className="h-full bg-action-primary transition-all"
              style={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
            />
          </div>
        )}
      </div>

      <Card>
        {step === 0 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.pickup')}</legend>
            <Field label={t('jobs:create.pickup.address')} required>
              {(p) => (
                <Input {...p} value={draft.pickupAddress} onChange={(e) => patch({ pickupAddress: e.target.value })} />
              )}
            </Field>
            <Field label={t('jobs:create.pickup.contactPhone')}>
              {(p) => (
                <Input
                  {...p}
                  type="tel"
                  value={draft.pickupContactPhone}
                  onChange={(e) => patch({ pickupContactPhone: e.target.value })}
                />
              )}
            </Field>
          </fieldset>
        )}

        {step === 1 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.destination')}</legend>
            <Field label={t('jobs:create.destination.address')} required>
              {(p) => (
                <Input
                  {...p}
                  value={draft.destinationAddress}
                  onChange={(e) => patch({ destinationAddress: e.target.value })}
                />
              )}
            </Field>
            <Field label={t('jobs:create.destination.recipientName')} required>
              {(p) => (
                <Input {...p} value={draft.recipientName} onChange={(e) => patch({ recipientName: e.target.value })} />
              )}
            </Field>
            <Field label={t('jobs:create.destination.recipientPhone')} hint={t('jobs:create.destination.phoneHint')}>
              {(p) => (
                <Input
                  {...p}
                  type="tel"
                  value={draft.recipientPhone}
                  onChange={(e) => patch({ recipientPhone: e.target.value })}
                />
              )}
            </Field>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.cargo')}</legend>
            <Field label={t('jobs:create.cargo.description')} required>
              {(p) => (
                <Input
                  {...p}
                  value={draft.cargoDescription}
                  onChange={(e) => patch({ cargoDescription: e.target.value })}
                  placeholder={t('jobs:create.cargo.descriptionPlaceholder')}
                />
              )}
            </Field>
            <Field label={t('jobs:create.cargo.category')}>
              {(p) => (
                <Input {...p} value={draft.cargoCategory} onChange={(e) => patch({ cargoCategory: e.target.value })} />
              )}
            </Field>
            <div className="space-y-2">
              {HANDLING_FLAGS.map((flag) => (
                <label key={flag} className="flex items-center gap-2 text-body-sm text-fg">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-line-strong"
                    checked={draft.handlingFlags.includes(flag)}
                    onChange={(e) =>
                      patch({
                        handlingFlags: e.target.checked
                          ? [...draft.handlingFlags, flag]
                          : draft.handlingFlags.filter((f) => f !== flag),
                      })
                    }
                  />
                  {t(`jobs:create.cargo.flag.${flag}`)}
                </label>
              ))}
              <label className="flex items-center gap-2 text-body-sm text-fg">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-line-strong"
                  checked={draft.hazardous}
                  onChange={(e) => patch({ hazardous: e.target.checked })}
                />
                {t('jobs:create.cargo.hazardous')}
              </label>
              {draft.hazardous && <Alert tone="warning">{t('jobs:create.cargo.hazardousWarning')}</Alert>}
            </div>
          </fieldset>
        )}

        {step === 3 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.weightSize')}</legend>
            <Field label={t('jobs:create.weight.estWeightKg')}>
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  min={0}
                  value={draft.estWeightKg}
                  onChange={(e) => patch({ estWeightKg: e.target.value })}
                />
              )}
            </Field>
            <label className="flex items-center gap-2 text-body-sm text-fg">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-line-strong"
                checked={draft.bulky}
                onChange={(e) => patch({ bulky: e.target.checked })}
              />
              {t('jobs:create.weight.bulky')}
            </label>
            {draft.bulky && (
              <div className="grid grid-cols-3 gap-2">
                <Field label={t('jobs:create.weight.dimsL')}>
                  {(p) => <Input {...p} type="number" min={0} value={draft.dimsL} onChange={(e) => patch({ dimsL: e.target.value })} />}
                </Field>
                <Field label={t('jobs:create.weight.dimsW')}>
                  {(p) => <Input {...p} type="number" min={0} value={draft.dimsW} onChange={(e) => patch({ dimsW: e.target.value })} />}
                </Field>
                <Field label={t('jobs:create.weight.dimsH')}>
                  {(p) => <Input {...p} type="number" min={0} value={draft.dimsH} onChange={(e) => patch({ dimsH: e.target.value })} />}
                </Field>
              </div>
            )}
          </fieldset>
        )}

        {step === 4 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.value')}</legend>
            <Field
              label={t('jobs:create.value.label')}
              hint={t('jobs:create.value.hint')}
              required
              error={draft.declaredValue && !step5Valid(draft) ? t('jobs:create.value.invalid') : undefined}
            >
              {(p) => (
                <Input
                  {...p}
                  inputMode="numeric"
                  value={draft.declaredValue}
                  onChange={(e) => patch({ declaredValue: e.target.value })}
                  placeholder="e.g. 12000"
                />
              )}
            </Field>
          </fieldset>
        )}

        {step === 5 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.vehicle')}</legend>
            <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label={t('jobs:create.steps.vehicle')}>
              {(vehicleTypes.data?.vehicle_types ?? []).map((code) => (
                <button
                  key={code}
                  type="button"
                  role="radio"
                  aria-checked={draft.vehicleClassCode === code}
                  onClick={() => patch({ vehicleClassCode: code })}
                  className={`rounded-md border p-3 text-left text-body-sm ${
                    draft.vehicleClassCode === code
                      ? 'border-line-focus bg-surface-brand-tint text-action-primary-hover'
                      : 'border-line-strong text-fg'
                  }`}
                >
                  {code.charAt(0) + code.slice(1).toLowerCase().replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        {step === 6 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.when')}</legend>
            <label className="flex items-center gap-2 text-body text-fg">
              <input
                type="radio"
                name="when"
                checked={draft.whenAsap}
                onChange={() => patch({ whenAsap: true })}
              />
              {t('jobs:create.when.asap')}
            </label>
            <label className="flex items-center gap-2 text-body text-fg">
              <input
                type="radio"
                name="when"
                checked={!draft.whenAsap}
                onChange={() => patch({ whenAsap: false })}
              />
              {t('jobs:create.when.scheduled')}
            </label>
            {!draft.whenAsap && (
              <Field label={t('jobs:create.when.dateTime')}>
                {(p) => <Input {...p} value={draft.whenNote} onChange={(e) => patch({ whenNote: e.target.value })} placeholder="e.g. Tomorrow 9am" />}
              </Field>
            )}
          </fieldset>
        )}

        {step === 7 && (
          <fieldset className="space-y-3">
            <legend className="text-h3 text-fg">{t('jobs:create.steps.delivery')}</legend>
            <Field label={t('jobs:create.delivery.requirements')}>
              {(p) => (
                <Input
                  {...p}
                  value={draft.deliveryRequirements}
                  onChange={(e) => patch({ deliveryRequirements: e.target.value })}
                />
              )}
            </Field>
            <Field label={t('jobs:create.delivery.proposedPrice')} hint={t('jobs:create.delivery.proposedPriceHint')}>
              {(p) => (
                <Input
                  {...p}
                  inputMode="numeric"
                  value={draft.proposedPrice}
                  onChange={(e) => patch({ proposedPrice: e.target.value })}
                  placeholder="e.g. 7800"
                />
              )}
            </Field>
          </fieldset>
        )}

        {isReview && (
          <div className="space-y-4">
            <p role="status" className="rounded-md bg-surface-brand-tint px-3 py-2 text-body-sm text-action-primary-hover">
              {t('jobs:create.draftBanner')}
            </p>
            <dl className="space-y-2 text-body-sm">
              <ReviewRow label={t('jobs:create.steps.pickup')} value={draft.pickupAddress} onEdit={() => setStep(0)} />
              <ReviewRow
                label={t('jobs:create.steps.destination')}
                value={`${draft.destinationAddress} — ${draft.recipientName}`}
                onEdit={() => setStep(1)}
              />
              <ReviewRow label={t('jobs:create.steps.cargo')} value={draft.cargoDescription} onEdit={() => setStep(2)} />
              <ReviewRow
                label={t('jobs:create.steps.value')}
                value={step5Valid(draft) ? formatKes(parseKesToMinorUnits(draft.declaredValue)!) : '—'}
                onEdit={() => setStep(4)}
              />
              <ReviewRow
                label={t('jobs:create.steps.vehicle')}
                value={draft.vehicleClassCode || '—'}
                onEdit={() => setStep(5)}
              />
              <ReviewRow
                label={t('jobs:create.steps.when')}
                value={draft.whenAsap ? t('jobs:create.when.asap') : draft.whenNote || '—'}
                onEdit={() => setStep(6)}
              />
              {draft.proposedPrice && (
                <ReviewRow
                  label={t('jobs:create.delivery.proposedPrice')}
                  value={parseKesToMinorUnits(draft.proposedPrice) ? formatKes(parseKesToMinorUnits(draft.proposedPrice)!) : '—'}
                  onEdit={() => setStep(7)}
                />
              )}
            </dl>
            {submitError && <Alert tone="danger">{submitError}</Alert>}
          </div>
        )}
      </Card>

      <div className="flex items-center justify-between gap-3">
        {step > 0 && (
          <Button variant="tertiary" onClick={() => setStep((s) => s - 1)} disabled={submitting}>
            {t('jobs:create.back')}
          </Button>
        )}
        <div className="ml-auto">
          {isReview ? (
            <Button onClick={() => void sendRequest()} loading={submitting}>
              {t('jobs:create.sendRequest')}
            </Button>
          ) : (
            <Button onClick={() => setStep((s) => s + 1)} disabled={!canAdvance}>
              {step === TOTAL_STEPS - 1 ? t('jobs:create.reviewRequest') : t('jobs:create.next')}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function ReviewRow({ label, value, onEdit }: { label: string; value: string; onEdit: () => void }): JSX.Element {
  const { t } = useTranslation('jobs');
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line pb-2">
      <div>
        <dt className="text-fg-muted">{label}</dt>
        <dd className="text-fg">{value}</dd>
      </div>
      <button type="button" onClick={onEdit} className="shrink-0 text-action-secondary-text underline">
        {t('jobs:create.edit')}
      </button>
    </div>
  );
}
