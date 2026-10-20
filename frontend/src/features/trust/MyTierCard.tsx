import { useQuery } from '@tanstack/react-query';

import { TierCard } from './TierCard';
import { trustApi } from './trustApi';

/** The signed-in operator's own tier (operator-tiers plan T-3). Shows
 * nothing while loading or when there's no operator profile; the rest of
 * the page doesn't depend on it. */
export function MyTierCard({ compact = false }: { compact?: boolean }): JSX.Element | null {
  const tier = useQuery({ queryKey: ['operator', 'me', 'tier'], queryFn: trustApi.myTier, retry: false });
  if (!tier.data) return null;
  return <TierCard view={tier.data} compact={compact} />;
}
