/**
 * Typed, validated access to the small set of build-time environment values the
 * client needs. Fail loud at startup rather than produce confusing runtime
 * errors later.
 */

function required(name: keyof ImportMetaEnv, fallback?: string): string {
  const value = import.meta.env[name] ?? fallback;
  if (value === undefined || value === '') {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const env = {
  apiBaseUrl: required('VITE_API_BASE_URL', 'http://localhost:8000/api/v1').replace(/\/+$/, ''),
  appName: required('VITE_APP_NAME', 'Fikisha'),
  isDev: import.meta.env.DEV,
} as const;
