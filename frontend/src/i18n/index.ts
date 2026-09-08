/**
 * i18n bootstrap. English + Swahili are first-class (Phase 0 — Swahili is
 * prominent on operator screens). Namespaces: `common`, `auth`, `errors`.
 */

import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import authEn from './locales/en/auth.json';
import commonEn from './locales/en/common.json';
import errorsEn from './locales/en/errors.json';
import authSw from './locales/sw/auth.json';
import commonSw from './locales/sw/common.json';
import errorsSw from './locales/sw/errors.json';

export const SUPPORTED_LANGUAGES = ['en', 'sw'] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const resources = {
  en: { common: commonEn, auth: authEn, errors: errorsEn },
  sw: { common: commonSw, auth: authSw, errors: errorsSw },
} as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LANGUAGES as unknown as string[],
    defaultNS: 'common',
    ns: ['common', 'auth', 'errors'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'fikisha.lang',
      caches: ['localStorage'],
    },
  });

export default i18n;
