import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';

/**
 * LandingPage — the public, unauthenticated entry point (`/`). Explains what
 * Fikisha is to a first-time visitor; no account/session required to read it.
 * Every call to action routes through `/login`, which redirects back here
 * (or to whatever route the visitor was trying to reach) once signed in.
 */
export function LandingPage(): JSX.Element {
  const { t } = useTranslation(['landing', 'common']);
  const navigate = useNavigate();

  return (
    <div className="space-y-10">
      <section className="space-y-4 py-6 text-center sm:py-10">
        <h1 className="text-h1 text-fg">{t('common:appName')}</h1>
        <p className="text-h3 font-normal text-fg-secondary">{t('landing:hero.tagline')}</p>
        <p className="mx-auto max-w-xl text-body text-fg-secondary">{t('landing:hero.lead')}</p>
        <div className="flex flex-col items-center gap-2 pt-2">
          <Button size="driver" onClick={() => navigate('/login')}>
            {t('landing:hero.signIn')}
          </Button>
          <p className="text-caption text-fg-muted">{t('landing:hero.signInNote')}</p>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="text-h3 text-fg">{t('landing:audiences.business.title')}</h2>
          <p className="mt-2 text-body-sm text-fg-secondary">
            {t('landing:audiences.business.body')}
          </p>
        </Card>
        <Card>
          <h2 className="text-h3 text-fg">{t('landing:audiences.operator.title')}</h2>
          <p className="mt-2 text-body-sm text-fg-secondary">
            {t('landing:audiences.operator.body')}
          </p>
        </Card>
      </section>

      <section className="space-y-2">
        <h2 className="text-label text-fg-secondary">{t('landing:how.title')}</h2>
        <p className="text-body-sm text-fg-secondary">{t('landing:how.body')}</p>
      </section>

      <section className="flex flex-col items-center gap-3 border-t border-line py-6 text-center">
        <p className="text-body text-fg">{t('landing:footer.cta')}</p>
        <Button variant="secondary" onClick={() => navigate('/login')}>
          {t('landing:footer.signIn')}
        </Button>
      </section>
    </div>
  );
}
