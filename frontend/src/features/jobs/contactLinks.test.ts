import { describe, expect, it } from 'vitest';

import { kenyanWhatsappNumber, mapsHref, telHref, whatsappHref } from './contactLinks';

describe('contactLinks', () => {
  it.each([
    ['+254 712 345 678', '254712345678'],
    ['254712345678', '254712345678'],
    ['0712345678', '254712345678'],
    ['0112-345-678', '254112345678'],
  ])('reads %s as a Kenyan WhatsApp number', (input, expected) => {
    expect(kenyanWhatsappNumber(input)).toBe(expected);
  });

  it.each(['', '12345', '+44 7700 900123', '0212345678', '07123456'])('gives no WhatsApp link for %j', (input) => {
    expect(whatsappHref(input)).toBeNull();
  });

  it('builds tel: links from the number as typed, and none for a blank number', () => {
    expect(telHref('+254 712 345 678')).toBe('tel:+254712345678');
    expect(telHref('0712 345 678')).toBe('tel:0712345678');
    expect(telHref('')).toBeNull();
    expect(telHref(null)).toBeNull();
  });

  it('prefers coordinates for the map hand-off, else the address, else nothing', () => {
    expect(mapsHref({ address_text: 'Depot', lat: '-1.47', lng: '36.96' })).toBe(
      'https://www.google.com/maps/search/?api=1&query=-1.47%2C36.96',
    );
    expect(mapsHref({ address_text: 'Shop 4, Kitengela', lat: null, lng: null })).toBe(
      'https://www.google.com/maps/search/?api=1&query=Shop%204%2C%20Kitengela',
    );
    expect(mapsHref({ address_text: '  ' })).toBeNull();
    expect(mapsHref(null)).toBeNull();
  });
});
