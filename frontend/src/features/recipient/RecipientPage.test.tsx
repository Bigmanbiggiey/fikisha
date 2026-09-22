import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';
import { ApiError } from '@/services/problem';

import { RecipientPage } from './RecipientPage';

const view = vi.fn();

vi.mock('@/features/jobs/recipientApi', () => ({
  recipientApi: { view: (...a: unknown[]) => view(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

function renderAtToken(token: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/r/:token" element={<RecipientPage />} />
    </Routes>,
    { route: `/r/${token}` },
  );
}

function baseView(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    delivery_reference: 'FK-1234',
    recipient_display_name: 'John M.',
    cargo_summary: '8 cartons · Electronics',
    status: 'IN_TRANSIT',
    status_label: 'In transit',
    driver_first_name: 'Samuel',
    vehicle_class: 'Pickup',
    vehicle_plate: 'KDG 123A',
    operator_identity_verified: true,
    allowed_actions: ['VIEW', 'CONFIRM_RECEIPT', 'REPORT_ISSUE'],
    ...overrides,
  };
}

describe('RecipientPage', () => {
  beforeEach(() => {
    view.mockReset();
  });

  it('while en route, shows only the status — no action buttons', async () => {
    view.mockResolvedValue(baseView());
    renderAtToken('tok123');

    expect(await screen.findByText('Delivery for John M.')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Confirm I received the goods' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Report a problem' })).not.toBeInTheDocument();
  });

  it('on arrival, offers Confirm receipt and Report a problem', async () => {
    view.mockResolvedValue(baseView({ status: 'AT_DESTINATION' }));
    renderAtToken('tok123');

    expect(await screen.findByRole('link', { name: 'Confirm I received the goods' })).toHaveAttribute(
      'href',
      '/r/tok123/confirm',
    );
    expect(screen.getByRole('link', { name: 'Report a problem' })).toHaveAttribute(
      'href',
      '/r/tok123/report-issue',
    );
  });

  it('once delivered, shows a read-only thank-you with no actions', async () => {
    view.mockResolvedValue(baseView({ status: 'DELIVERED' }));
    renderAtToken('tok123');

    expect(await screen.findByText('Delivery confirmed — thank you')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Confirm I received the goods' })).not.toBeInTheDocument();
  });

  it('an expired/revoked link shows the expiry message, not the generic invalid message', async () => {
    view.mockRejectedValue(
      new ApiError(
        {
          type: 'about:blank',
          title: 'Gone',
          status: 410,
          code: 'recipient_link_inactive',
          detail: 'This link is no longer active.',
        },
        410,
        'This link is no longer active.',
      ),
    );
    renderAtToken('tok123');

    expect(
      await screen.findByText("This link has expired. Ask the sender or driver for a new one."),
    ).toBeInTheDocument();
  });

  it('an unknown token shows the generic invalid-link message', async () => {
    view.mockRejectedValue(
      new ApiError(
        { type: 'about:blank', title: 'Not found', status: 404, code: 'recipient_link_not_found', detail: 'Not found.' },
        404,
        'Not found.',
      ),
    );
    renderAtToken('not-a-real-token');

    expect(await screen.findByText("This link isn't valid.")).toBeInTheDocument();
  });
});
