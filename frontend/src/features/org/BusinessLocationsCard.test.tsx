import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { BusinessLocationsCard } from './BusinessLocationsCard';

const addLocation = vi.fn();
const updateLocation = vi.fn();

vi.mock('./orgApi', () => ({
  orgApi: {
    addLocation: (...a: unknown[]) => addLocation(...a),
    updateLocation: (...a: unknown[]) => updateLocation(...a),
    removeLocation: vi.fn(),
  },
}));
// Leaflet can't draw in jsdom: a stand-in that "drops a pin" when clicked.
vi.mock('@/features/maps/LocationPicker', () => ({
  LocationPicker: ({ onChange, label }: { onChange: (p: { lat: number; lng: number }) => void; label: string }) => (
    <button type="button" onClick={() => onChange({ lat: -1.4775, lng: 36.9601 })}>
      {`pin on ${label}`}
    </button>
  ),
}));
vi.mock('@/features/maps/mapConfig', async (orig) => {
  const actual = await orig<typeof import('@/features/maps/mapConfig')>();
  return { ...actual, mapConfigured: () => true };
});
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

const old = {
  id: 'l1',
  label: 'Old shop',
  type: 'MAIN',
  address_text: '',
  lat: null,
  lng: null,
  zone_code: null,
  contact_name: '',
  contact_phone: '',
  hours: {},
  access_notes: '',
};

describe('BusinessLocationsCard (maps M-2)', () => {
  beforeEach(() => {
    addLocation.mockReset().mockResolvedValue({});
    updateLocation.mockReset().mockResolvedValue({});
  });

  it('needs a pin before a new location can be saved, and sends it with the name', async () => {
    const user = userEvent.setup();
    renderWithProviders(<BusinessLocationsCard businessId="b1" locations={[]} canManage />);
    await user.type(screen.getByLabelText(/Name of this location/), 'Namanga Road store');
    const save = screen.getByRole('button', { name: 'Save location' });
    expect(save).toBeDisabled();
    expect(screen.getByText('Put the pin on the map first.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /pin on Map: where the new location is/ }));
    expect(save).toBeEnabled();
    await user.click(save);
    await waitFor(() =>
      expect(addLocation).toHaveBeenCalledWith('b1', {
        label: 'Namanga Road store',
        type: 'MAIN',
        address_text: '',
        lat: '-1.477500',
        lng: '36.960100',
      }),
    );
  });

  it('lets a location saved before maps get its pin', async () => {
    const user = userEvent.setup();
    renderWithProviders(<BusinessLocationsCard businessId="b1" locations={[old]} canManage />);
    expect(screen.getByText('No pin on the map yet')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Add the pin' }));
    await user.click(screen.getByRole('button', { name: /pin on Map: where Old shop is/ }));
    await user.click(screen.getByRole('button', { name: 'Save the pin' }));
    await waitFor(() =>
      expect(updateLocation).toHaveBeenCalledWith('b1', 'l1', { lat: '-1.477500', lng: '36.960100' }),
    );
  });
});
