import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { Card } from '@/components/Card';

import { notesQueryKey, opsApi } from './opsApi';

/**
 * "Updates from Fikisha" — operational notes staff post on a job (P3 §18.2
 * "nudge"; founder decision 2026-09-23: visible to the job's parties).
 * Renders nothing until there is at least one note, so an ordinary job's
 * detail page is unchanged. Parties see only "Fikisha Operations" as the
 * author (minimum disclosure — the backend never sends them the staff
 * member's identity).
 */
export function JobNotesSection({ jobId }: { jobId: string }): JSX.Element | null {
  const { t } = useTranslation('ops');
  const notes = useQuery({
    queryKey: notesQueryKey(jobId),
    queryFn: () => opsApi.notes(jobId),
    retry: false,
  });
  const items = notes.data?.data ?? [];
  if (items.length === 0) return null;

  return (
    <Card>
      <h2 className="text-label text-fg-secondary">{t('notes.title')}</h2>
      <ul className="mt-2 space-y-3">
        {items.map((note) => (
          <li key={note.id} className="border-l-2 border-line-strong pl-3">
            <p className="whitespace-pre-line text-body text-fg">{note.text}</p>
            <p className="mt-1 text-body-sm text-fg-muted">
              {note.author_label} · {new Date(note.created_at).toLocaleString()}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
