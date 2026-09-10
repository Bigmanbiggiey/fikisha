import { StatusBadge } from './StatusBadge';
import { JOB_STATE_VISUAL, type JobState } from '@/design/tokens';

/**
 * JobStatusChip — the approved visual for any of the 14 authoritative Job states
 * (Design Phase 4 §13). Underlying state names are unchanged; the label shown is
 * the approved working EN label (final EN/SW wording is a design-track detail and
 * will come from i18n). Colour is always paired with an icon and the text label.
 */
export function JobStatusChip({
  state,
  label,
}: {
  state: JobState;
  /** Override the label (e.g. a localized string). Defaults to the approved EN. */
  label?: string;
}): JSX.Element {
  const v = JOB_STATE_VISUAL[state];
  return <StatusBadge tone={v.tone} variant={v.chip} icon={v.icon} label={label ?? v.labelEn} />;
}
