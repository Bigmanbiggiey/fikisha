import { useEffect, useState } from 'react';

import { breakpoint } from './tokens';

export type Breakpoint = 'base' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

const ORDER: Breakpoint[] = ['base', 'sm', 'md', 'lg', 'xl', '2xl'];
const MIN_PX: Record<Exclude<Breakpoint, 'base'>, number> = {
  sm: parseInt(breakpoint.sm, 10),
  md: parseInt(breakpoint.md, 10),
  lg: parseInt(breakpoint.lg, 10),
  xl: parseInt(breakpoint.xl, 10),
  '2xl': parseInt(breakpoint['2xl'], 10),
};

function current(width: number): Breakpoint {
  let bp: Breakpoint = 'base';
  for (const key of ['sm', 'md', 'lg', 'xl', '2xl'] as const) {
    if (width >= MIN_PX[key]) bp = key;
  }
  return bp;
}

/**
 * useBreakpoint — the active Fikisha breakpoint (Phase 4 §25). Use for
 * *contextual adaptation* (e.g. Operator: single column → workspace layout), not
 * proportional scaling. SSR-safe default is `base`.
 */
export function useBreakpoint(): Breakpoint {
  const [bp, setBp] = useState<Breakpoint>(() =>
    typeof window === 'undefined' ? 'base' : current(window.innerWidth),
  );
  useEffect(() => {
    const onResize = (): void => setBp(current(window.innerWidth));
    window.addEventListener('resize', onResize);
    onResize();
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return bp;
}

/** True when the active breakpoint is `min` or wider. */
export function atLeast(bp: Breakpoint, min: Breakpoint): boolean {
  return ORDER.indexOf(bp) >= ORDER.indexOf(min);
}
