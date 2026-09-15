/**
 * A person's Fikisha "workspace" (Business / Operator / Group Manager /
 * Operations Officer / Platform Admin) is not one flat account field — it's
 * derived from which BusinessMembership / OperatorProfile / GroupMembership
 * rows exist for them (`docs/design-phase-1-ia.md` §5-§10), plus the
 * identity-level admin roles already on `AuthUser`. "Driver" deliberately
 * has no standalone workspace here: per IA §4.3/§7, it's a role-*scoped
 * view* a group DRIVER sees only in `DRIVER_ACCEPTS` mode, or a mode a solo
 * operator enters contextually (an active assigned Job) — not something to
 * switch into, so it isn't resolved by this module. See
 * `docs/design-phase-6-jobs-frontend-plan.md` §3.1/§4.
 */

export const WORKSPACE_KINDS = [
  'BUSINESS',
  'OPERATOR',
  'GROUP_MANAGER',
  'OPERATIONS_OFFICER',
  'PLATFORM_ADMIN',
] as const;
export type WorkspaceKind = (typeof WORKSPACE_KINDS)[number];

export interface Workspace {
  kind: WorkspaceKind;
  /** The underlying business/operator/group id this workspace is scoped to
   * — `null` for the two identity-level admin workspaces, which aren't
   * scoped to a single org. */
  id: string | null;
  label: string;
}
