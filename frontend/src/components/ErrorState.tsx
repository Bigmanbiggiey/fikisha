import { useTranslation } from 'react-i18next';

import { Alert } from './Alert';
import { Button } from './Button';

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}): JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="space-y-3">
      <Alert tone="error">{message}</Alert>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {t('actions.retry')}
        </Button>
      )}
    </div>
  );
}
