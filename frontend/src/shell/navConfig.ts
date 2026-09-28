import type { IconName } from '@/design/Icon';

/**
 * The role navigation (Design Phase 7 P-04, F-04): the P1 §26 matrix as
 * data, limited to screens that exist today. Rendered as a bottom tab bar on
 * phones (`RoleTabBar`), a persistent sidebar on desktop (`RoleSidebar`) and
 * the More page. UX only: every route is still authorised server-side.
 *
 * Deliberately absent until their screens exist: Business "Messages"
 * (sub-increment 10g), Group Manager "Team", Ops "Incidents / Disputes"
 * lists and "Search", Platform Admin "Control" (Increment 9), statements,
 * help and settings. Diagnostics is left out of user navigation; it stays
 * reachable at /diagnostics.
 */

export const NAV_ROLES = [
  'BUSINESS',
  'OPERATOR',
  'DRIVER',
  'GROUP_MANAGER',
  'OPERATIONS_OFFICER',
  'PLATFORM_ADMIN',
] as const;
export type NavRole = (typeof NAV_ROLES)[number];

export interface NavItem {
  to: string;
  /** i18n key (namespaces `common` / `org`) */
  labelKey: string;
  icon: IconName;
  /** active only on an exact match (e.g. `/ops`, not `/ops/jobs`) */
  end?: boolean;
  /** extra path prefixes that also count as this item */
  alsoActive?: string[];
  /** paths that never count as this item, even under its prefix */
  notActive?: string[];
}

export interface RoleNav {
  primary: NavItem[];
  secondary: NavItem[];
  /** the role's main call to action, shown as a tab on phones and a button
   * at the top of the sidebar (Business "Request transport", P1 §5) */
  action?: NavItem;
}

const home: NavItem = { to: '/home', labelKey: 'common:nav.home', icon: 'home', end: true };
const vehicles: NavItem = { to: '/vehicles', labelKey: 'org:nav.vehicles', icon: 'truck' };
const profile: NavItem = { to: '/operator', labelKey: 'org:nav.operator', icon: 'badge' };
const groups: NavItem = { to: '/groups', labelKey: 'org:nav.groups', icon: 'handshake' };

const staff: RoleNav = {
  primary: [
    { to: '/ops', labelKey: 'common:nav.ops', icon: 'home', end: true },
    { to: '/ops/jobs', labelKey: 'common:nav.opsJobs', icon: 'list' },
    { to: '/verification', labelKey: 'org:nav.verification', icon: 'badge' },
  ],
  secondary: [
    { to: '/ops/high-value', labelKey: 'common:nav.highValue', icon: 'flag' },
    { to: '/ops/audit', labelKey: 'common:nav.audit', icon: 'eye' },
  ],
};

export const NAV: Record<NavRole, RoleNav> = {
  BUSINESS: {
    primary: [home, { to: '/jobs', labelKey: 'common:nav.jobs', icon: 'list', notActive: ['/jobs/new'] }],
    action: { to: '/jobs/new', labelKey: 'common:nav.requestTransport', icon: 'plus', end: true },
    secondary: [{ to: '/businesses', labelKey: 'org:nav.businesses', icon: 'box' }],
  },
  OPERATOR: {
    primary: [
      home,
      { to: '/work', labelKey: 'common:nav.work', icon: 'send' },
      { to: '/my-jobs', labelKey: 'common:nav.myJobs', icon: 'list' },
    ],
    secondary: [
      vehicles,
      profile,
      { to: '/operating-locations', labelKey: 'org:nav.locations', icon: 'pin' },
      groups,
    ],
  },
  DRIVER: {
    primary: [
      // A driver's job pages are part of "Current job", not of "Jobs".
      { to: '/current-job', labelKey: 'common:nav.currentJob', icon: 'truck', alsoActive: ['/jobs/'] },
      { to: '/my-jobs', labelKey: 'common:nav.jobs', icon: 'list' },
    ],
    secondary: [profile],
  },
  GROUP_MANAGER: {
    primary: [home, { to: '/my-jobs', labelKey: 'common:nav.jobs', icon: 'list' }],
    secondary: [groups, vehicles],
  },
  OPERATIONS_OFFICER: staff,
  // Same as Operations until the Platform Admin console (Increment 9).
  PLATFORM_ADMIN: staff,
};

/**
 * For a signed-in person with no role yet (no business, operator profile or
 * group): Home, plus the screens where they set one up, and More (which
 * holds language and sign out). Without this a new user on a phone had no
 * navigation and no way to sign out.
 */
export const SETUP_NAV: RoleNav = {
  primary: [home],
  secondary: [{ to: '/businesses', labelKey: 'org:nav.businesses', icon: 'box' }, profile],
};

/** The navigation to show: the active role's, or the setup set. */
export function navFor(role: NavRole | null): RoleNav {
  return role ? NAV[role] : SETUP_NAV;
}

/** Default when a person holds several roles and hasn't picked one. */
export const ROLE_PRIORITY: readonly NavRole[] = NAV_ROLES;

/** Where "switch to this role" lands. */
export function roleHomePath(role: NavRole): string {
  return NAV[role].primary[0]!.to;
}

export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (item.notActive?.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return false;
  if (pathname === item.to) return true;
  if (!item.end && pathname.startsWith(`${item.to}/`)) return true;
  return !!item.alsoActive?.some((p) => pathname.startsWith(p));
}
