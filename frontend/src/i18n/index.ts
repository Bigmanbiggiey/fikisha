/**
 * i18n bootstrap. English + Swahili are first-class (Phase 0 — Swahili is
 * prominent on operator screens). Namespaces: `common`, `auth`, `errors`,
 * `org`, `landing`.
 */

import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import authEn from './locales/en/auth.json';
import commonEn from './locales/en/common.json';
import errorsEn from './locales/en/errors.json';
import jobsEn from './locales/en/jobs.json';
import landingEn from './locales/en/landing.json';
import negotiationEn from './locales/en/negotiation.json';
import orgEn from './locales/en/org.json';
import recipientEn from './locales/en/recipient.json';
import authSw from './locales/sw/auth.json';
import commonSw from './locales/sw/common.json';
import errorsSw from './locales/sw/errors.json';
import jobsSw from './locales/sw/jobs.json';
import landingSw from './locales/sw/landing.json';
import negotiationSw from './locales/sw/negotiation.json';
import orgSw from './locales/sw/org.json';
import recipientSw from './locales/sw/recipient.json';

export const SUPPORTED_LANGUAGES = ['en', 'sw'] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const resources = {
  en: {
    common: commonEn,
    auth: authEn,
    errors: errorsEn,
    org: orgEn,
    landing: landingEn,
    jobs: jobsEn,
    negotiation: negotiationEn,
    recipient: recipientEn,
  },
  sw: {
    common: commonSw,
    auth: authSw,
    errors: errorsSw,
    org: orgSw,
    landing: landingSw,
    jobs: jobsSw,
    negotiation: negotiationSw,
    recipient: recipientSw,
  },
} as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LANGUAGES as unknown as string[],
    defaultNS: 'common',
    ns: ['common', 'auth', 'errors', 'org', 'landing', 'jobs', 'negotiation', 'recipient'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'fikisha.lang',
      caches: ['localStorage'],
    },
  });

export default i18n;
