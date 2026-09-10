import type { SVGProps } from 'react';

/**
 * Fikisha icon set — Design Phase 5B.
 * One style: outline, 1.75px stroke, 24px grid, rounded caps/joins (Phase 4 §5.7).
 * `currentColor` for stroke and (where relevant) fill, so an icon takes the
 * colour of its surrounding text. Meaningful icons must be given a label by the
 * caller (`title` or an adjacent text node); decorative icons stay aria-hidden.
 */

export type IconName =
  | 'check'
  | 'flagCheck'
  | 'dotCurrent'
  | 'circle'
  | 'slash'
  | 'alertTriangle'
  | 'alert'
  | 'pause'
  | 'pencil'
  | 'send'
  | 'chat'
  | 'handshake'
  | 'badge'
  | 'pin'
  | 'pinCheck'
  | 'box'
  | 'truck'
  | 'dot'
  | 'ellipsis'
  | 'eye'
  | 'sync'
  | 'flag'
  | 'close'
  | 'back'
  | 'chevronRight'
  | 'phone'
  | 'camera'
  | 'lock';

interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  name: IconName;
  /** px size for width & height. Default 20. */
  size?: number;
  /** Accessible name. When omitted the icon is aria-hidden (decorative). */
  title?: string;
}

// Path/element content per icon. Stroke unless noted; `dot`/`dotCurrent` fill.
const PATHS: Record<IconName, JSX.Element> = {
  check: <path d="M4 12.5l5 5 11-12" />,
  flagCheck: (
    <>
      <path d="M5 21V4h13l-3 4 3 4H5" />
      <path d="M8.5 8.5l2 2 4-4.5" />
    </>
  ),
  dotCurrent: <circle cx="12" cy="12" r="5" fill="currentColor" stroke="none" />,
  circle: <circle cx="12" cy="12" r="7" />,
  slash: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M7 7l10 10" />
    </>
  ),
  alertTriangle: (
    <>
      <path d="M12 4L2.5 20h19L12 4z" />
      <path d="M12 10v5" />
      <circle cx="12" cy="17.5" r="0.6" fill="currentColor" stroke="none" />
    </>
  ),
  alert: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5v5" />
      <circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none" />
    </>
  ),
  pause: (
    <>
      <rect x="7" y="5" width="3.5" height="14" rx="1" />
      <rect x="13.5" y="5" width="3.5" height="14" rx="1" />
    </>
  ),
  pencil: <path d="M4 20h4L20 8l-4-4L4 16v4z M14 6l4 4" />,
  send: <path d="M4 12l16-7-7 16-2-7-7-2z" />,
  chat: <path d="M4 5h16v11H9l-5 4V5z" />,
  handshake: <path d="M3 12l4-4 5 4 5-4 4 4-6 6-3-3-3 3-6-6z" />,
  badge: (
    <>
      <rect x="5" y="4" width="14" height="16" rx="2" />
      <circle cx="12" cy="10" r="2.5" />
      <path d="M8 17c1-2 7-2 8 0" />
    </>
  ),
  pin: (
    <>
      <path d="M12 21s7-6.5 7-12a7 7 0 10-14 0c0 5.5 7 12 7 12z" />
      <circle cx="12" cy="9" r="2.5" />
    </>
  ),
  pinCheck: (
    <>
      <path d="M12 21s7-6.5 7-12a7 7 0 10-14 0c0 5.5 7 12 7 12z" />
      <path d="M9 9l2 2 4-4" />
    </>
  ),
  box: (
    <>
      <path d="M4 8l8-4 8 4v8l-8 4-8-4V8z" />
      <path d="M4 8l8 4 8-4M12 12v8" />
    </>
  ),
  truck: (
    <>
      <path d="M3 6h11v9H3zM14 9h4l3 3v3h-7z" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="17" cy="18" r="2" />
    </>
  ),
  dot: <circle cx="12" cy="12" r="5" fill="currentColor" stroke="none" />,
  ellipsis: (
    <>
      <circle cx="6" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="18" cy="12" r="1.4" fill="currentColor" stroke="none" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  sync: <path d="M4 12a8 8 0 0113.5-5.8L20 8M20 4v4h-4M20 12a8 8 0 01-13.5 5.8L4 16M4 20v-4h4" />,
  flag: <path d="M6 21V4h11l-2.5 4L17 12H6" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  back: <path d="M14 6l-6 6 6 6" />,
  chevronRight: <path d="M9 6l6 6-6 6" />,
  phone: <path d="M6 3h4l2 5-3 2a12 12 0 006 6l2-3 5 2v4c0 1-1 2-2 2A17 17 0 014 6c0-1 1-3 2-3z" />,
  camera: (
    <>
      <path d="M4 8h4l1.5-2h5L16 8h4v11H4z" />
      <circle cx="12" cy="13" r="3.5" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="10" width="14" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 018 0v3" />
    </>
  ),
};

export function Icon({ name, size = 20, title, ...rest }: IconProps): JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      {PATHS[name]}
    </svg>
  );
}
