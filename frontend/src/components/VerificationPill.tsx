import { StatusBadge } from './StatusBadge';
import {
  VERIFICATION_GROUP_OF,
  VERIFICATION_GROUP_VISUAL,
  type VerificationGroup,
  type VerificationState,
} from '@/design/tokens';

/**
 * VerificationPill — Design Phase 4 §16/§30.8. A factual pill:
 * `[domain] · [status]`. Renders the 5 user-facing groups; the 7 authoritative
 * verification states are unchanged. "Needs attention" = INFO_REQUESTED +
 * REJECTED + effective EXPIRED. Never a score, never stars, never a blanket
 * "Verified operator" badge.
 */
export function VerificationPill({
  domain,
  state,
  group,
  groupLabel,
  hideDomain = false,
}: {
  /** human domain name, e.g. "Identity", "Driving licence" */
  domain?: string;
  /** the authoritative state (mapped to a group) … */
  state?: VerificationState;
  /** … or pass the group directly */
  group?: VerificationGroup;
  groupLabel?: string;
  /** show only the group (when the domain is already labelled nearby) */
  hideDomain?: boolean;
}): JSX.Element {
  const g: VerificationGroup = group ?? (state ? VERIFICATION_GROUP_OF[state] : 'required');
  const v = VERIFICATION_GROUP_VISUAL[g];
  const text = groupLabel ?? v.labelEn;
  return (
    <StatusBadge
      tone={v.tone}
      variant="soft"
      icon={v.icon}
      label={hideDomain || !domain ? text : `${domain} · ${text}`}
    />
  );
}
