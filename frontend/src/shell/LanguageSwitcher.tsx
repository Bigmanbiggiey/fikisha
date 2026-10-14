import { useTranslation } from 'react-i18next';

import { Select } from '@/components/Select';

import { SUPPORTED_LANGUAGES, type SupportedLanguage } from '@/i18n';

export function LanguageSwitcher(): JSX.Element {
  const { t, i18n } = useTranslation('common');
  const current = (i18n.resolvedLanguage ?? 'en') as SupportedLanguage;

  return (
    <label className="flex items-center gap-2 text-body-sm">
      <span className="sr-only">{t('language.label')}</span>
      <Select
        aria-label={t('language.label')}
        value={current}
        onChange={(e) => void i18n.changeLanguage(e.target.value)}
        inline
      >
        {SUPPORTED_LANGUAGES.map((lng) => (
          <option key={lng} value={lng}>
            {t(`language.${lng}`)}
          </option>
        ))}
      </Select>
    </label>
  );
}
