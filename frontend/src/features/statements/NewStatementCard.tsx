import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Card } from '@/components/Card';
import { useAuth } from '@/features/auth/useAuth';
import { formatKes } from '@/features/jobs/money';

import { periodLabel } from './statementFormat';
import { statementsApi, statementsQueryKey } from './statementsApi';

/**
 * Home "New statement" (D-6: in the app only, no SMS/WhatsApp yet). Shows
 * the newest statement the person hasn't opened; nothing otherwise.
 */
export function NewStatementCard(): JSX.Element | null {
  const { t, i18n } = useTranslation('statements');
  const { user } = useAuth();
  const list = useQuery({
    queryKey: [...statementsQueryKey, 'list', 'home', user?.id],
    queryFn: () => statementsApi.list(),
    staleTime: 60_000,
    retry: false,
  });
  const page = list.data;
  const newest = page?.data.find((s) => s.seen === false);
  if (!page || page.unseen_count === 0 || !newest) return null;
  return (
    <Card className="border-action-primary">
      <h2 className="text-label text-action-primary">
        {t('home.title', { count: page.unseen_count })}
      </h2>
      <p className="mt-1 text-body text-fg">
        {t('home.body', {
          period: periodLabel(newest, i18n.resolvedLanguage),
          amount: formatKes(Math.max(newest.net_due_kes, 0)),
        })}
      </p>
      <Link
        to={`/statements/${newest.id}`}
        className="mt-2 inline-flex min-h-target items-center text-body font-semibold text-action-secondary-text underline"
      >
        {t('home.view')}
      </Link>
    </Card>
  );
}
