/** Every `*_kes` field from the backend is an integer in KES **minor units**
 * (cents) — `fikisha.common.money.Money`, `CLAUDE.md` §4 "integer KES minor
 * units everywhere". `formatKes(400000)` → "KSh 4,000". */
export function formatKes(minorUnits: number): string {
  const major = minorUnits / 100;
  return `KSh ${major.toLocaleString('en-KE', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

/** Parse a user-typed whole-KES amount (e.g. from a form field) into minor
 * units for the API. Returns `null` for anything that isn't a positive
 * number. */
export function parseKesToMinorUnits(input: string): number | null {
  const cleaned = input.replace(/[,\s]/g, '');
  if (!cleaned || !/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  const major = Number(cleaned);
  if (!Number.isFinite(major) || major <= 0) return null;
  return Math.round(major * 100);
}
