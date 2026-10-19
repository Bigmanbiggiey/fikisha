/**
 * The Kenyan phone rule (founder assessment 2026-10-20 L-3, LD-2), the same
 * as the server's `fikisha.identity.phone`: `07…` or `01…`, or `+254…` where
 * `+254` stands for the leading `0`; exactly 10 digits after that, otherwise
 * refused. `+254100350768` → `0100350768`; `+25472345689` → `072345689` (9
 * digits) is refused. The server stores `+254…`; people see `07…`.
 */

const NATIONAL = /^0[17]\d{8}$/;
const SEPARATORS = /[\s\-().]/g;

/** The national form (`07…` / `01…`) of a valid number, or null. */
export function kenyanNational(input: string): string | null {
  let cleaned = (input ?? '').trim().replace(SEPARATORS, '');
  if (cleaned.startsWith('+254')) cleaned = `0${cleaned.slice(4)}`;
  return NATIONAL.test(cleaned) ? cleaned : null;
}

export function isValidKenyanPhone(input: string): boolean {
  return kenyanNational(input) !== null;
}

/** An optional phone field is fine empty; otherwise it must be valid. */
export function isOptionalPhoneOk(input: string): boolean {
  return input.trim() === '' || isValidKenyanPhone(input);
}

/** How a stored number is shown: `+254712345678` → `0712345678`. */
export function displayPhone(phone: string | null | undefined): string {
  if (!phone) return '';
  return /^\+254\d{9}$/.test(phone) ? `0${phone.slice(4)}` : phone;
}
