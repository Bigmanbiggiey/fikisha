import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { JobMap } from './JobMap';
import { mapsHref } from '@/features/jobs/contactLinks';

// Leaflet can't draw in jsdom.
vi.mock('./LeafletView', () => ({ default: () => <div>map</div> }));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

describe('JobMap (maps M-4)', () => {
  it('gives directions to each exact pin', async () => {
    renderWithProviders(
      <JobMap
        pickup={{ lat: '-1.477500', lng: '36.960100', geo_state: 'CAPTURED' }}
        destination={{ lat: '-1.500000', lng: '36.950000', geo_state: 'CAPTURED' }}
      />,
    );
    const links = await screen.findAllByRole('link', { name: 'Open in Google Maps' });
    expect(links.map((a) => a.getAttribute('href'))).toEqual([
      'https://www.google.com/maps/dir/?api=1&destination=-1.477500,36.960100',
      'https://www.google.com/maps/dir/?api=1&destination=-1.500000,36.950000',
    ]);
  });

  it('shows only the area, and no directions, before the job is assigned to the viewer', async () => {
    renderWithProviders(
      <JobMap pickup={null} destination={{ lat: '-1.48', lng: '36.96', geo_state: 'COARSENED' }} />,
    );
    expect(await screen.findByText(/Only the area is shown for now/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Open in Google Maps' })).not.toBeInTheDocument();
  });

  it('renders nothing without a pin', () => {
    const { container } = renderWithProviders(<JobMap pickup={{ lat: null, lng: null }} destination={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('never points the driver at rounded coordinates', () => {
    expect(mapsHref({ address_text: 'Shop 4', lat: '-1.48', lng: '36.96', geo_state: 'COARSENED' })).toBe(
      'https://www.google.com/maps/search/?api=1&query=Shop%204',
    );
  });
});
