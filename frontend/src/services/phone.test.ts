import { describe, expect, it } from 'vitest';

import { displayPhone, isOptionalPhoneOk, kenyanNational } from './phone';

describe('Kenyan phone rule (assessment 2026-10-20 L-3)', () => {
  it.each([
    ['0712345678', '0712345678'],
    ['0100350768', '0100350768'],
    ['+254100350768', '0100350768'],
    ['+254 712 345 678', '0712345678'],
  ])('accepts %s as %s', (input, national) => {
    expect(kenyanNational(input)).toBe(national);
  });

  it.each(['+25472345689', '071234567', '07123456789', '254712345678', '0812345678', '+447911123456', ''])(
    'refuses %s',
    (input) => {
      expect(kenyanNational(input)).toBeNull();
    },
  );

  it('shows stored numbers in the national form and allows an empty optional field', () => {
    expect(displayPhone('+254712345678')).toBe('0712345678');
    expect(isOptionalPhoneOk('')).toBe(true);
    expect(isOptionalPhoneOk('07')).toBe(false);
  });
});
