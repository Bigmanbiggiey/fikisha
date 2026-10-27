/**
 * A commission rate from the server ("0.0500") as a percentage ("5%"). Display
 * only: every fee amount is computed by the server (ADR-2D-55).
 */
export function formatRate(rate: string | number): string {
  const pct = Math.round(Number(rate) * 10000) / 100;
  return `${Number.isFinite(pct) ? pct : 0}%`;
}
