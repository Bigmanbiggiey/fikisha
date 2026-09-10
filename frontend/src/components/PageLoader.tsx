import { useTranslation } from 'react-i18next';

import { Spinner } from './Spinner';

export function PageLoader(): JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-action-primary">
      <Spinner className="h-6 w-6" label={t('actions.loading')} />
    </div>
  );
}
