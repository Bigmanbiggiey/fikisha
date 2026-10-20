import { useTranslation } from 'react-i18next';

import { Card } from '@/components/Card';
import { Icon } from '@/design/Icon';

import type { ProofGroups, ProofMethod } from './custodyProof';

/**
 * "This pickup needs: …" with each requirement ticked off as it is given
 * (assessment 2026-10-20 L-5). Text and an icon, never colour alone.
 */
export function ProofChecklist({
  title,
  groups,
  present,
}: {
  title: string;
  groups: ProofGroups;
  present: ReadonlySet<ProofMethod>;
}): JSX.Element {
  const { t } = useTranslation('jobs');
  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{title}</h2>
      <ul className="mt-2 space-y-2 text-body">
        {groups.map((group) => {
          const met = group.some((m) => present.has(m));
          const label = group.map((m) => t(`proof.method.${m}`)).join(t('proof.or'));
          return (
            <li key={group.join('|')} className="flex items-center gap-2">
              <span className={met ? 'text-status-success-fg' : 'text-fg-muted'}>
                <Icon name={met ? 'check' : 'circle'} size={20} />
              </span>
              <span className={met ? 'text-fg' : 'text-fg-secondary'}>{label}</span>
              <span className="sr-only">{met ? t('proof.done') : t('proof.todo')}</span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
