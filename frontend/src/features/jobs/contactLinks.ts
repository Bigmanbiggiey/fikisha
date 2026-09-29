/**
 * Contact and map hand-off links for the driver's Current Job (Design
 * Phase 7 P-03, P3 §10.1). Links only: the phone's own dialler, WhatsApp
 * and map app do the work. No map embed, no GPS (not in MVP).
 */

/** `tel:` href for a phone as the business typed it, or null if blank. */
export function telHref(phone: string | null | undefined): string | null {
  const cleaned = (phone ?? '').replace(/[^0-9+]/g, '');
  return cleaned ? `tel:${cleaned}` : null;
}

/**
 * The number as `wa.me` needs it (country code, digits only), for numbers
 * we can read as Kenyan: +2547…/+2541…, 2547…/2541…, 07…/01…. Anything
 * else returns null and the caller shows Call only, rather than a WhatsApp
 * link that might open the wrong chat.
 */
export function kenyanWhatsappNumber(phone: string | null | undefined): string | null {
  const digits = (phone ?? '').replace(/[^0-9]/g, '');
  if (/^254[17]\d{8}$/.test(digits)) return digits;
  if (/^0[17]\d{8}$/.test(digits)) return `254${digits.slice(1)}`;
  return null;
}

export function whatsappHref(phone: string | null | undefined): string | null {
  const number = kenyanWhatsappNumber(phone);
  return number ? `https://wa.me/${number}` : null;
}

/** Opens the place in the phone's map app: coordinates when present, else
 * the address text. Null when there's nothing to search for. */
export function mapsHref(
  location: { address_text?: string | null; lat?: string | number | null; lng?: string | number | null } | null | undefined,
): string | null {
  if (!location) return null;
  const hasCoords = location.lat != null && location.lat !== '' && location.lng != null && location.lng !== '';
  const query = hasCoords ? `${location.lat},${location.lng}` : (location.address_text ?? '').trim();
  return query ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}` : null;
}
