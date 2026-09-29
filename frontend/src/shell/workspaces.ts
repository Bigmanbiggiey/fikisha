/**
 * A person's Fikisha "workspace" (Business / Operator / Driver / Group
 * Manager / Operations Officer / Platform Admin) is not one flat account
 * field — it's derived from which BusinessMembership / OperatorProfile /
 * GroupMembership rows exist for them (`docs/design-phase-1-ia.md` §5-§10),
 * plus the identity-level admin roles already on `AuthUser`.
 *
 * `DRIVER` (Design Phase 7 P-04, founder ruling 2026-09-28): one per group
 * where the person's membership role is DRIVER (IA §4.3: "a GroupMembership
 * with role = DRIVER"). It picks the narrower Driver navigation. A group
 * driver still has an operator profile, so they keep the `OPERATOR`
 * workspace too; that one carries their operator id for job-level checks
 * (`useJobViewerRole`). An individual operator acting as their own driver
 * gets no `DRIVER` workspace: the driver screen comes to them in context,
 * on their assigned jobs.
 */

export const WORKSPACE_KINDS = [
  'BUSINESS',
  'OPERATOR',
  'DRIVER',
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
  /** DRIVER only: the group's assignment mode. A group driver sees
   * available work only in `DRIVER_ACCEPTS` (IA §4.3, §7). */
  assignmentMode?: string;
}
