import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, useLocation } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Field } from '@/components/Field';
import { Input } from '@/components/Input';
import { localizeError } from '@/services/errorMessage';

import { authApi } from './authApi';
import { useAuth } from './useAuth';

type Step = 'phone' | 'code';

interface LocationState {
  from?: string;
}

export function LoginPage(): JSX.Element {
  const { t } = useTranslation(['auth', 'common', 'errors']);
  const { status, completeLogin } = useAuth();
  const location = useLocation();
  const from = (location.state as LocationState | null)?.from ?? '/';

  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [challengeId, setChallengeId] = useState('');
  const [devCode, setDevCode] = useState<string | undefined>();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === 'authenticated') return <Navigate to={from} replace />;

  async function onRequestCode(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await authApi.requestOtp(phone.trim());
      setChallengeId(result.challenge_id);
      setDevCode(result.dev_code);
      if (result.dev_code) setCode(result.dev_code);
      setStep('code');
    } catch (err) {
      setError(localizeError(err, t));
    } finally {
      setBusy(false);
    }
  }

  async function onVerify(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await authApi.verifyOtp(challengeId, code.trim());
      completeLogin(result);
    } catch (err) {
      setError(localizeError(err, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4">
      <Card>
        <h1 className="text-h1 text-fg">{t('auth:login.title')}</h1>
        <p className="mt-1 text-body-sm text-fg-muted">{t('auth:login.subtitle')}</p>

        {error && (
          <div className="mt-4">
            <Alert tone="danger">{error}</Alert>
          </div>
        )}

        {step === 'phone' ? (
          <form className="mt-5 space-y-4" onSubmit={onRequestCode}>
            <Field label={t('auth:login.phoneLabel')}>
              {({ id }) => (
                <Input
                  id={id}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  required
                  placeholder={t('auth:login.phonePlaceholder')}
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              )}
            </Field>
            <Button type="submit" fullWidth loading={busy}>
              {t('auth:login.requestCode')}
            </Button>
          </form>
        ) : (
          <form className="mt-5 space-y-4" onSubmit={onVerify}>
            <p className="text-body-sm text-fg-secondary">
              {t('auth:login.codeSentTo', { phone: phone.trim() })}
            </p>
            {devCode && (
              <Alert tone="warning">{t('auth:login.devCodeNotice', { code: devCode })}</Alert>
            )}
            <Field label={t('auth:login.codeLabel')}>
              {({ id }) => (
                <Input
                  id={id}
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  placeholder={t('auth:login.codePlaceholder')}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              )}
            </Field>
            <Button type="submit" fullWidth loading={busy}>
              {t('auth:login.verify')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              fullWidth
              onClick={() => {
                setStep('phone');
                setCode('');
                setError(null);
              }}
            >
              {t('auth:login.back')}
            </Button>
          </form>
        )}
      </Card>
    </div>
  );
}
