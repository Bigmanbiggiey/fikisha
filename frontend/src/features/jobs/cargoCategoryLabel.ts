import { useTranslation } from 'react-i18next';

/** "MEDICAL_SUPPLIES" → "Medical supplies" for a category added after this
 * build shipped (it has no translation yet). */
function humanise(code: string): string {
  const words = code.toLowerCase().split('_').join(' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function useCargoCategoryLabel(): (code: string) => string {
  const { t } = useTranslation('jobs');
  return (code) => t(`cargoCategory.${code}`, { defaultValue: humanise(code) });
}
