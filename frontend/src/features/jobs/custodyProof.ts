/**
 * What a pickup or delivery needs (founder assessment 2026-10-20 L-5, LD-4):
 * the server sends each job's rule as groups (`custody_requirements`); every
 * group must be met, a group by any one of its methods. The server checks it
 * again; this only drives the checklist and the button.
 */

export type ProofMethod = 'OTP' | 'SIGNATURE' | 'PHOTO' | 'IN_APP';
export type ProofGroups = ProofMethod[][];

/** Used only if an older server sends no rule: today's STANDARD rule. */
export const FALLBACK_PICKUP: ProofGroups = [['OTP', 'SIGNATURE', 'PHOTO', 'IN_APP']];
export const FALLBACK_DELIVERY: ProofGroups = [['OTP', 'SIGNATURE']];

export function unmetGroups(groups: ProofGroups, present: ReadonlySet<ProofMethod>): ProofGroups {
  return groups.filter((g) => !g.some((m) => present.has(m)));
}

/** Every method the rule mentions: which inputs to offer. */
export function methodsIn(groups: ProofGroups): Set<ProofMethod> {
  return new Set(groups.flat());
}
