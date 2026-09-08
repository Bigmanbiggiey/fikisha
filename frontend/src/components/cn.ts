/** Tiny class-name joiner — avoids a dependency for trivial conditional classes. */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}
