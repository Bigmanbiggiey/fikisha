import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/Button';
import { AdminActionDialog } from '@/features/admin/AdminActionDialog';
import { formatDateTime } from '@/services/datetime';

import { type CancellationFlagRow, opsApi } from './opsApi';
import { Queue } from './Queue';

const KEY = ['ops', 'cancellation-flags'];

/**
 * Businesses that reached three late cancellations or wasted trips in 30
 * days (D-DIS-3, trust plan A7). A review item only: staff clear it with a
 * note, or close it as mistaken; nothing changes automatically.
 */
export function CancellationFlagsCard(): JSX.Element | null {
  const { t } = useTranslation(['ops', 'errors']);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: KEY, queryFn: opsApi.cancellationFlags, retry: false });
  const [pending, setPending] = useState<{ flag: CancellationFlagRow; mistaken: boolean } | null>(null);
  const review = useMutation({
    mutationFn: (note: string) =>
      opsApi.reviewCancellationFlag(pending!.flag.id, {
        outcome: pending!.mistaken ? 'MISTAKEN' : 'CLEARED',
        note,
      }),
    onSuccess: () => {
      setPending(null);
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
  const rows = q.data?.data ?? [];
  if (rows.length === 0) return null;
  return (
    <>
      <Queue title={t('ops:cancellationFlags.title')} count={rows.length} more={false}>
        {rows.map((f) => (
          <li key={f.id} className="rounded-md border border-line px-3 py-2">
            <span className="block text-body font-semibold text-fg">{f.business_name}</span>
            <span className="block text-body-sm text-fg-muted">
              {t('ops:cancellationFlags.row', { count: f.count })} · {formatDateTime(f.created_at)}
            </span>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  review.reset();
                  setPending({ flag: f, mistaken: false });
                }}
              >
                {t('ops:cancellationFlags.clear')}
              </Button>
              <Button
                variant="tertiary"
                onClick={() => {
                  review.reset();
                  setPending({ flag: f, mistaken: true });
                }}
              >
                {t('ops:cancellationFlags.mistaken')}
              </Button>
            </div>
          </li>
        ))}
      </Queue>
      <AdminActionDialog
        open={pending !== null}
        onClose={() => setPending(null)}
        title={t(pending?.mistaken ? 'ops:cancellationFlags.mistakenTitle' : 'ops:cancellationFlags.clearTitle')}
        restatement={t(
          pending?.mistaken ? 'ops:cancellationFlags.mistakenRestate' : 'ops:cancellationFlags.clearRestate',
          { name: pending?.flag.business_name ?? '' },
        )}
        confirmLabel={t(pending?.mistaken ? 'ops:cancellationFlags.mistaken' : 'ops:cancellationFlags.clear')}
        pending={review.isPending}
        error={review.error}
        onConfirm={({ reason }) => review.mutate(reason)}
      />
    </>
  );
}
