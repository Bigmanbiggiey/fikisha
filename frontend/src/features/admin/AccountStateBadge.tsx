import { useTranslation } from 'react-i18next';

import { StatusBadge, type BadgeTone } from '@/components/StatusBadge';

const TONE: Record<string, BadgeTone> = {
  GOOD: 'success',
  ACTIVE: 'success',
  PENDING: 'info',
  RESTRICTED: 'warning',
  SUSPENDED: 'danger',
  OFFBOARDED: 'neutral',
};

/** An account's standing / status, as text plus tone (never colour only). */
export function AccountStateBadge({ state }: { state: string }): JSX.Element {
  const { t } = useTranslation('admin');
  return <StatusBadge tone={TONE[state] ?? 'neutral'} label={t(`state.${state}`, { defaultValue: state })} />;
}
