import qrcode from 'qrcode-generator';
import { useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Input } from '@/components/Input';
import { localizeError } from '@/services/errorMessage';

import { authApi } from './authApi';
import { useAuth } from './useAuth';

/**
 * Admin MFA (Increment 9a, ADR-2D-39; Phase 1 auth §1.2). Shown instead of
 * the app to an admin whose session hasn't passed MFA: their roles don't
 * apply until it has. First time: set up an authenticator app (QR code or
 * setup key), confirm with its first code, keep the backup codes. After
 * that: enter a code from the app, or a backup code.
 */
export function MfaPage(): JSX.Element {
  const { user, reloadMe, logout } = useAuth();
  const { t } = useTranslation(['auth', 'errors']);
  const enrolled = Boolean(user?.mfa?.enrolled);

  return (
    <div className="mx-auto max-w-md space-y-4 py-4">
      <div>
        <h1 className="text-h1 text-fg">{t(enrolled ? 'auth:mfa.verifyTitle' : 'auth:mfa.enrolTitle')}</h1>
        <p className="mt-1 text-body-sm text-fg-secondary">
          {t(enrolled ? 'auth:mfa.verifyIntro' : 'auth:mfa.enrolIntro')}
        </p>
      </div>
      {enrolled ? <Verify onDone={() => void reloadMe()} /> : <Enrol onDone={() => void reloadMe()} />}
      <Button variant="tertiary" onClick={() => void logout()}>
        {t('auth:mfa.signOut')}
      </Button>
    </div>
  );
}

function CodeForm({
  id,
  label,
  submitLabel,
  onSubmit,
}: {
  id: string;
  label: string;
  submitLabel: string;
  onSubmit: (code: string) => Promise<void>;
}): JSX.Element {
  const { t } = useTranslation(['auth', 'errors']);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent): Promise<void> {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(code.trim());
    } catch (err) {
      setError(localizeError(err, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="space-y-3" onSubmit={(e) => void submit(e)}>
      <label htmlFor={id} className="block text-label text-fg-secondary">
        {label}
      </label>
      <Input id={id} autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} />
      {error && <Alert tone="danger">{error}</Alert>}
      <Button type="submit" fullWidth loading={busy} disabled={!code.trim()}>
        {submitLabel}
      </Button>
    </form>
  );
}

function Verify({ onDone }: { onDone: () => void }): JSX.Element {
  const { t } = useTranslation('auth');
  return (
    <Card className="space-y-3">
      <CodeForm
        id="mfa-verify-code"
        label={t('auth:mfa.codeLabel')}
        submitLabel={t('auth:mfa.verify')}
        onSubmit={async (code) => {
          await authApi.mfaVerify(code);
          onDone();
        }}
      />
      <p className="text-body-sm text-fg-muted">{t('auth:mfa.backupHint')}</p>
    </Card>
  );
}

function Qr({ uri }: { uri: string }): JSX.Element {
  const { t } = useTranslation('auth');
  const svg = useMemo(() => {
    const qr = qrcode(0, 'M');
    qr.addData(uri);
    qr.make();
    return qr.createSvgTag({ cellSize: 5, margin: 2, scalable: true });
  }, [uri]);
  return (
    <img
      src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`}
      alt={t('auth:mfa.qrLabel')}
      className="mx-auto block w-56 max-w-full rounded-md bg-white p-2"
    />
  );
}

function Enrol({ onDone }: { onDone: () => void }): JSX.Element {
  const { t } = useTranslation(['auth', 'errors']);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function start(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      setSetup(await authApi.mfaEnroll());
    } catch (err) {
      setError(localizeError(err, t));
    } finally {
      setBusy(false);
    }
  }

  if (codes) {
    return (
      <Card className="space-y-3">
        <h2 className="text-h3 text-fg">{t('auth:mfa.backupTitle')}</h2>
        <p className="text-body-sm text-fg-secondary">{t('auth:mfa.backupBody')}</p>
        <ul className="grid grid-cols-2 gap-2 font-mono text-body" aria-label={t('auth:mfa.backupTitle')}>
          {codes.map((c) => (
            <li key={c} className="fk-numeric rounded-sm bg-surface-sunken px-2 py-1 text-center">
              {c}
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              navigator.clipboard
                ?.writeText(codes.join('\n'))
                .then(() => setCopied(true))
                .catch(() => setCopied(false));
            }}
          >
            {copied ? t('auth:mfa.copied') : t('auth:mfa.copy')}
          </Button>
          <Button onClick={onDone}>{t('auth:mfa.savedContinue')}</Button>
        </div>
      </Card>
    );
  }

  if (!setup) {
    return (
      <Card className="space-y-3">
        <ol className="list-decimal space-y-1 pl-5 text-body-sm text-fg-secondary">
          <li>{t('auth:mfa.step1')}</li>
          <li>{t('auth:mfa.step2')}</li>
          <li>{t('auth:mfa.step3')}</li>
        </ol>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button fullWidth loading={busy} onClick={() => void start()}>
          {t('auth:mfa.start')}
        </Button>
      </Card>
    );
  }

  return (
    <Card className="space-y-4">
      <Qr uri={setup.otpauth_uri} />
      <div>
        <p className="text-body-sm text-fg-secondary">{t('auth:mfa.manualKey')}</p>
        <p className="fk-numeric mt-1 break-all rounded-sm bg-surface-sunken px-2 py-1 font-mono text-body text-fg">
          {setup.secret.replace(/(.{4})/g, '$1 ').trim()}
        </p>
      </div>
      <CodeForm
        id="mfa-enrol-code"
        label={t('auth:mfa.firstCodeLabel')}
        submitLabel={t('auth:mfa.confirm')}
        onSubmit={async (code) => {
          const result = await authApi.mfaEnrollConfirm(code);
          setCodes(result.backup_codes);
        }}
      />
    </Card>
  );
}
