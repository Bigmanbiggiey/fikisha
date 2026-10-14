import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { isRetryable } from '@/services/errorMessage';

import { Alert } from './Alert';
import { Button } from './Button';

/**
 * ErrorState — Design Phase 5B. What happened (the message) + what to do.
 * Pass the `error`: when retrying can't help (Increment 10f), it offers a
 * way Home instead of a "Try again" that would fail the same way.
 */
export function ErrorState({
  message,
  onRetry,
  error,
}: {
  message: string;
  onRetry?: () => void;
  error?: unknown;
}): JSX.Element {
  const { t } = useTranslation();
  const retry = onRetry && isRetryable(error);
  return (
    <div className="space-y-3">
      <Alert tone="danger">{message}</Alert>
      {retry ? (
        <Button variant="secondary" onClick={onRetry}>
          {t('actions.retry')}
        </Button>
      ) : (
        error !== undefined &&
        !isRetryable(error) && (
          <Link to="/home" className="inline-block text-body text-action-secondary-text underline">
            {t('actions.goHome')}
          </Link>
        )
      )}
    </div>
  );
}
