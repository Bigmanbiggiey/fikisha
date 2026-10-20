import L from 'leaflet';

/**
 * A map pin drawn in CSS (no image files to bundle, and Leaflet's default
 * marker images break under a bundler). The colour comes from the design
 * tokens through Tailwind classes; the pin carries a text letter so the two
 * pins on a job map differ by more than colour.
 */
export function pinIcon(tone: 'brand' | 'pickup' | 'destination', letter = ''): L.DivIcon {
  const colour =
    tone === 'destination' ? 'bg-status-danger-fg' : tone === 'pickup' ? 'bg-status-info-fg' : 'bg-action-primary';
  return L.divIcon({
    className: '',
    html: `<span class="flex h-8 w-8 -translate-x-1/2 -translate-y-full items-center justify-center rounded-full border-2 border-fg-inverse ${colour} text-caption font-bold text-fg-inverse shadow-md">${letter}</span>`,
    iconSize: [0, 0],
  });
}
