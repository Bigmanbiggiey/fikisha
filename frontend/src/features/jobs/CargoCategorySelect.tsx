import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Select } from '@/components/Select';

import { useCargoCategoryLabel } from './cargoCategoryLabel';
import { jobsApi } from './jobsApi';

/**
 * The cargo category picker (assessment 2026-10-19 D-5): the configured
 * categories, in English or Swahili. Given the cargo `description`, it fills
 * itself in from the server's keyword suggestion until the person picks one
 * themselves. Left on "Let Fikisha choose", the server picks the same way.
 */
export function CargoCategorySelect({
  value,
  onChange,
  description,
  ...rest
}: {
  value: string;
  onChange: (code: string) => void;
  /** suggest from this text (debounced) */
  description?: string;
  id?: string;
  'aria-describedby'?: string;
}): JSX.Element {
  const { t } = useTranslation('jobs');
  const label = useCargoCategoryLabel();
  const categories = useQuery({
    queryKey: ['reference', 'cargoCategories'],
    queryFn: jobsApi.cargoCategories,
    staleTime: 5 * 60_000,
  });

  const [touched, setTouched] = useState(false);
  const [text, setText] = useState(description ?? '');
  useEffect(() => {
    const handle = window.setTimeout(() => setText(description ?? ''), 400);
    return () => window.clearTimeout(handle);
  }, [description]);
  const suggestion = useQuery({
    queryKey: ['reference', 'cargoCategorySuggest', text.trim().toLowerCase()],
    queryFn: () => jobsApi.suggestCargoCategory(text),
    enabled: description !== undefined && !touched && text.trim().length >= 3,
    staleTime: 60_000,
  });
  const suggested = suggestion.data?.code ?? null;
  useEffect(() => {
    if (!touched && suggested && suggested !== value) onChange(suggested);
  }, [suggested, touched, value, onChange]);

  return (
    <>
      <Select
        {...rest}
        value={value}
        onChange={(e) => {
          setTouched(true);
          onChange(e.target.value);
        }}
      >
        <option value="">{t('cargoCategory.auto')}</option>
        {(categories.data?.data ?? []).map((c) => (
          <option key={c.code} value={c.code}>
            {label(c.code)}
          </option>
        ))}
      </Select>
      {!touched && suggested && value === suggested && (
        <p className="mt-1 text-caption text-fg-muted">{t('cargoCategory.suggested')}</p>
      )}
    </>
  );
}
