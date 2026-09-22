import { LanguageSwitcher } from '@/shell/LanguageSwitcher';

/**
 * RecipientHeader — Design Phase 6 Increment 6. The only "chrome" a
 * recipient sees: a small Fikisha mark + the EN|SW toggle
 * (`design-phase-3-wireframes.md` §20.1). No `TopBar`/`AppShell` — the
 * recipient has no account, no workspace, no nav. `LanguageSwitcher` is
 * reused unmodified; it has no auth/workspace dependency.
 */
export function RecipientHeader(): JSX.Element {
  return (
    <header className="flex items-center justify-between border-b border-line px-4 py-3">
      <span className="text-h3 font-bold text-action-primary">fikisha</span>
      <LanguageSwitcher />
    </header>
  );
}
