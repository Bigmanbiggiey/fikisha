/**
 * Service-worker registration. Phase 2A ships an app-shell precache only —
 * no API responses are cached. The offline-safe vs server-confirmed split
 * (Phase 1 pwa-architecture) is implemented with the delivery features in 2B.
 */
export async function registerServiceWorker(): Promise<void> {
  if (import.meta.env.DEV) return;
  try {
    const { registerSW } = await import('virtual:pwa-register');
    registerSW({ immediate: true });
  } catch {
    // PWA plugin not available (e.g. test env) — safe to ignore.
  }
}
