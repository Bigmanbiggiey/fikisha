import { describe, expect, it } from 'vitest';

import { entryStatusLabel } from './negotiationHelpers';

describe('entryStatusLabel', () => {
  it('labels an ACTIVE ACCEPT as accepted', () => {
    expect(entryStatusLabel({ type: 'ACCEPT', effective_status: 'ACTIVE' })).toBe('accepted');
  });

  it('regression: a SUPERSEDED ACCEPT reads as countered, not accepted', () => {
    // The business accepted an offer, then the operator countered before
    // reciprocating — selectors.annotate_entries() marks the now-voided
    // ACCEPT entry SUPERSEDED. It must not still show "Accepted".
    expect(entryStatusLabel({ type: 'ACCEPT', effective_status: 'SUPERSEDED' })).toBe('countered');
  });

  it('an EXPIRED ACCEPT reads as declined', () => {
    expect(entryStatusLabel({ type: 'ACCEPT', effective_status: 'EXPIRED' })).toBe('declined');
  });

  it('a REJECT always reads as declined regardless of effective_status', () => {
    expect(entryStatusLabel({ type: 'REJECT', effective_status: 'ACTIVE' })).toBe('declined');
  });

  it('labels PROPOSE/COUNTER entries by effective_status', () => {
    expect(entryStatusLabel({ type: 'PROPOSE', effective_status: 'ACTIVE' })).toBe('current');
    expect(entryStatusLabel({ type: 'COUNTER', effective_status: 'EXPIRED' })).toBe('expired');
    expect(entryStatusLabel({ type: 'COUNTER', effective_status: 'SUPERSEDED' })).toBe('countered');
  });
});
