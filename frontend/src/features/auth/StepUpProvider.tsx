import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { Modal } from '@/components/Modal';
import { setStepUpHandler } from '@/services/apiClient';
import { localizeError } from '@/services/errorMessage';

import { authApi } from './authApi';

/**
 * The step-up prompt (Increment 9a, ADR-2D-39). When a sensitive action
 * answers `step_up_required`, the API client calls the handler registered
 * here: this dialog asks for a fresh authenticator code, and on success the
 * original request is retried. Requests that hit the error together share
 * one prompt. Cancelling leaves the action refused.
 */
export function StepUpProvider({ children }: { children: ReactNode }): JSX.Element {
  const { t } = useTranslation(['auth', 'errors']);
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<{ promise: Promise<boolean>; resolve: (ok: boolean) => void } | null>(null);

  const ask = useCallback((): Promise<boolean> => {
    if (pending.current) return pending.current.promise;
    let resolve: (ok: boolean) => void = () => {};
    const promise = new Promise<boolean>((r) => {
      resolve = r;
    });
    pending.current = { promise, resolve };
    setCode('');
    setError(null);
    setOpen(true);
    return promise;
  }, []);

  useEffect(() => {
    setStepUpHandler(ask);
    return () => setStepUpHandler(null);
  }, [ask]);

  function finish(ok: boolean): void {
    pending.current?.resolve(ok);
    pending.current = null;
    setOpen(false);
  }

  async function submit(e: FormEvent): Promise<void> {
    e.preventDefault();
    if (!code.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await authApi.stepUp(code.trim());
      finish(true);
    } catch (err) {
      setError(localizeError(err, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {children}
      <Modal
        open={open}
        onClose={() => finish(false)}
        title={t('auth:stepUp.title')}
        footer={
          <>
            <Button variant="secondary" onClick={() => finish(false)}>
              {t('auth:stepUp.cancel')}
            </Button>
            <Button type="submit" form="step-up-form" loading={busy} disabled={!code.trim()}>
              {t('auth:stepUp.confirm')}
            </Button>
          </>
        }
      >
        <form id="step-up-form" className="space-y-3" onSubmit={(e) => void submit(e)}>
          <p className="text-body-sm text-fg-secondary">{t('auth:stepUp.body')}</p>
          <label htmlFor="step-up-code" className="block text-label text-fg-secondary">
            {t('auth:mfa.codeLabel')}
          </label>
          <Input
            id="step-up-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          {error && <Alert tone="danger">{error}</Alert>}
        </form>
      </Modal>
    </>
  );
}
