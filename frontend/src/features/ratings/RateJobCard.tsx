import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { cn } from '@/components/cn';
import { Textarea } from '@/components/Textarea';
import { localizeError } from '@/services/errorMessage';

import { ratingsApi, ratingsQueryKey } from './ratingsApi';
import type { RatingItem } from './types';

const SCORES = [1, 2, 3, 4, 5] as const;

/**
 * Rating a completed job (trust-and-disputes plan A4). Each side rates the
 * other once, within 7 days of completion; a rating shows to the rated side
 * once both have rated or the time is up, and only staff read comments.
 * Hidden for anyone the server says can't see the job's ratings.
 */
export function RateJobCard({ jobId }: { jobId: string }): JSX.Element | null {
  const { t } = useTranslation(['ratings', 'errors']);
  const qc = useQueryClient();
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const view = useQuery({
    queryKey: ratingsQueryKey(jobId),
    queryFn: () => ratingsApi.forJob(jobId),
    retry: false,
  });
  const submit = useMutation({
    mutationFn: () => ratingsApi.submit(jobId, { score: score!, comment }),
    onSuccess: (data) => qc.setQueryData(ratingsQueryKey(jobId), data),
  });

  if (!view.data) return null;
  const v = view.data;

  if (v.ratings) {
    return (
      <Card className="space-y-2">
        <h2 className="text-label text-fg-secondary">{t('staffTitle')}</h2>
        {v.ratings.length === 0 ? (
          <p className="text-body-sm text-fg-muted">{t('none')}</p>
        ) : (
          <ul className="space-y-2">
            {v.ratings.map((r) => (
              <StaffRow key={r.id} rating={r} />
            ))}
          </ul>
        )}
      </Card>
    );
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-label text-fg-secondary">
        {v.side === 'BUSINESS_RATES_OPERATOR' ? t('titleOperator') : t('titleBusiness')}
      </h2>
      {v.mine && (
        <p className="text-body text-fg">{t('yourRating', { score: v.mine.score })}</p>
      )}
      {v.about_me && (
        <p className="text-body text-fg">
          {t('theirRating', { score: v.about_me.score })}
          {!v.about_me.counted && (
            <span className="block text-caption text-fg-muted">{t('notCounted')}</span>
          )}
        </p>
      )}
      {v.can_rate && (
        <div className="space-y-2">
          <div role="group" aria-label={t('scoreLabel')} className="flex gap-2">
            {SCORES.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={score === s}
                aria-label={t('scoreOption', { score: s })}
                onClick={() => setScore(s)}
                className={cn(
                  'h-11 w-11 rounded-md border text-body font-semibold',
                  score === s
                    ? 'border-action-primary bg-action-primary text-action-on-primary'
                    : 'border-line-strong text-fg',
                )}
              >
                {s}
              </button>
            ))}
          </div>
          <p className="text-caption text-fg-muted">{t('scale')}</p>
          <Textarea
            aria-label={t('comment')}
            placeholder={t('comment')}
            value={comment}
            maxLength={1000}
            onChange={(e) => setComment(e.target.value)}
          />
          <p className="text-caption text-fg-muted">{t('commentHint')}</p>
          <Button disabled={score === null} loading={submit.isPending} onClick={() => submit.mutate()}>
            {t('submit')}
          </Button>
          {submit.isError && <Alert tone="danger">{localizeError(submit.error, t)}</Alert>}
        </div>
      )}
      {!v.can_rate && !v.mine && <p className="text-body-sm text-fg-muted">{t('closed')}</p>}
      {v.mine && !v.about_me && <p className="text-caption text-fg-muted">{t('waiting')}</p>}
    </Card>
  );
}

function StaffRow({ rating }: { rating: RatingItem }): JSX.Element {
  const { t } = useTranslation('ratings');
  return (
    <li className="text-body-sm">
      <span className="font-semibold text-fg">
        {t(`side.${rating.side}`)}: {t('outOf5', { score: rating.score })}
      </span>
      <span className="block text-fg-secondary">
        {rating.published ? (rating.counted ? t('counted') : t('notCounted')) : t('unpublished')}
      </span>
      {rating.comment && <span className="block text-fg">{rating.comment}</span>}
    </li>
  );
}
