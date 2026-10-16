import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { Modal } from '@/components/Modal';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { formatKes, parseKesToMinorUnits } from '@/features/jobs/money';
import { formatDate } from '@/services/datetime';
import { localizeError } from '@/services/errorMessage';

import { kenyaToday } from './statementFormat';
import type { PaymentInput, StatementDetail } from './types';

const METHODS: PaymentInput['method'][] = ['MPESA_PAYBILL', 'BANK', 'OTHER'];

/**
 * Record a payment against a statement (D-4): amount, M-Pesa (or bank)
 * reference, the date it was paid, then a confirm step that restates it.
 * The server asks for a fresh authenticator code, refuses more than is
 * still owed and refuses a reference already recorded.
 */
export function RecordPaymentDialog({
  open,
  statement,
  pending,
  error,
  onClose,
  onConfirm,
}: {
  open: boolean;
  statement: StatementDetail;
  pending: boolean;
  error: unknown;
  onClose: () => void;
  onConfirm: (input: PaymentInput) => void;
}): JSX.Element {
  const { t, i18n } = useTranslation(['statements', 'errors']);
  const today = kenyaToday();
  const [step, setStep] = useState<'form' | 'confirm'>('form');
  const [amount, setAmount] = useState('');
  const [reference, setReference] = useState('');
  const [paidOn, setPaidOn] = useState(today);
  const [method, setMethod] = useState<PaymentInput['method']>('MPESA_PAYBILL');
  const [note, setNote] = useState('');

  const minor = parseKesToMinorUnits(amount);
  const tooMuch = minor !== null && minor > statement.outstanding_kes;
  const ref = reference.trim().toUpperCase();
  const dateValid = /^\d{4}-\d{2}-\d{2}$/.test(paidOn) && paidOn <= today;
  const ready = minor !== null && !tooMuch && ref.length > 0 && dateValid;

  function close(): void {
    setStep('form');
    setAmount('');
    setReference('');
    setPaidOn(today);
    setMethod('MPESA_PAYBILL');
    setNote('');
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title={t('statements:admin.recordTitle', { reference: statement.reference })}
      footer={
        step === 'form' ? (
          <>
            <Button variant="secondary" onClick={close}>
              {t('statements:admin.cancel')}
            </Button>
            <Button disabled={!ready} onClick={() => setStep('confirm')}>
              {t('statements:admin.continue')}
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" onClick={() => setStep('form')}>
              {t('statements:admin.back')}
            </Button>
            <Button
              loading={pending}
              onClick={() =>
                onConfirm({
                  amount_kes: minor!,
                  payment_ref: ref,
                  paid_on: paidOn,
                  method,
                  note: note.trim(),
                })
              }
            >
              {t('statements:admin.recordConfirm')}
            </Button>
          </>
        )
      }
    >
      <div className="space-y-3">
        <Alert tone="info">{t('statements:admin.mfaNotice')}</Alert>
        {step === 'form' ? (
          <>
            <div className="space-y-1">
              <label htmlFor="payment-amount" className="block text-label text-fg-secondary">
                {t('statements:admin.amount')}
              </label>
              <Input
                id="payment-amount"
                inputMode="decimal"
                value={amount}
                invalid={amount !== '' && (minor === null || tooMuch)}
                aria-describedby="payment-amount-hint"
                onChange={(e) => setAmount(e.target.value)}
              />
              <p id="payment-amount-hint" className="text-body-sm text-fg-muted">
                {tooMuch
                  ? t('statements:admin.amountTooMuch', {
                      amount: formatKes(statement.outstanding_kes),
                    })
                  : t('statements:admin.amountHint', {
                      amount: formatKes(statement.outstanding_kes),
                    })}
              </p>
            </div>
            <div className="space-y-1">
              <label htmlFor="payment-ref" className="block text-label text-fg-secondary">
                {t('statements:admin.reference')}
              </label>
              <Input
                id="payment-ref"
                value={reference}
                maxLength={64}
                autoCapitalize="characters"
                onChange={(e) => setReference(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label htmlFor="payment-date" className="block text-label text-fg-secondary">
                  {t('statements:admin.paidOn')}
                </label>
                <Input
                  id="payment-date"
                  type="date"
                  value={paidOn}
                  max={today}
                  invalid={!dateValid}
                  onChange={(e) => setPaidOn(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="payment-method" className="block text-label text-fg-secondary">
                  {t('statements:admin.method')}
                </label>
                <Select
                  id="payment-method"
                  value={method}
                  onChange={(e) => setMethod(e.target.value as PaymentInput['method'])}
                >
                  {METHODS.map((m) => (
                    <option key={m} value={m}>
                      {t(`statements:admin.methodOption.${m}`)}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <label htmlFor="payment-note" className="block text-label text-fg-secondary">
                {t('statements:admin.note')}
              </label>
              <Textarea
                id="payment-note"
                value={note}
                maxLength={500}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>
          </>
        ) : (
          <>
            <p className="text-body font-semibold text-fg">
              {t('statements:admin.recordRestate', {
                amount: formatKes(minor ?? 0),
                payee: statement.payee.name ?? '—',
                reference: statement.reference,
              })}
            </p>
            <p className="text-body-sm text-fg-secondary">
              {t('statements:admin.recordDetails', {
                ref,
                date: formatDate(paidOn, i18n.resolvedLanguage),
                method: t(`statements:admin.methodOption.${method}`),
              })}
            </p>
            <p className="text-body-sm text-fg-muted">{t('statements:admin.audited')}</p>
          </>
        )}
        {error != null && <Alert tone="danger">{localizeError(error, t)}</Alert>}
      </div>
    </Modal>
  );
}
