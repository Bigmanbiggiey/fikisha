import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/renderWithProviders';

import { ApplicantPage } from './ApplicantPage';
import { VerificationQueuePage } from './VerificationQueuePage';

const applicants = vi.fn();
const applicant = vi.fn();
const approveOperator = vi.fn();

vi.mock('./verificationApi', async (orig) => {
  const actual = await orig<typeof import('./verificationApi')>();
  return {
    ...actual,
    verificationApi: {
      ...actual.verificationApi,
      applicants: (...a: unknown[]) => applicants(...a),
      applicant: (...a: unknown[]) => applicant(...a),
      approveOperator: (...a: unknown[]) => approveOperator(...a),
    },
  };
});
vi.mock('@/features/auth/authApi', () => ({
  authApi: {
    me: () =>
      Promise.resolve({
        id: 'staff1',
        phone: '+254700000009',
        display_name: 'Reviewer',
        locale: 'en',
        status: 'ACTIVE',
        roles: ['OPERATIONS_OFFICER'],
        is_admin: true,
      }),
    logout: vi.fn(),
  },
}));

const page = { next_cursor: null, prev_cursor: null };

describe('verification queue by applicant (assessment 2026-10-19 part 5)', () => {
  beforeEach(() => {
    applicants.mockReset();
    applicant.mockReset();
    approveOperator.mockReset();
  });

  it('has a tab per kind of user and one row per applicant', async () => {
    applicants.mockImplementation((kind: string) =>
      Promise.resolve({
        data:
          kind === 'OPERATOR'
            ? [
                {
                  kind: 'OPERATOR',
                  id: 'op1',
                  name: 'BIGG-MOVERS',
                  status: 'PENDING',
                  open_count: 2,
                  oldest_open_at: '2026-10-19T06:00:00Z',
                  created_at: '2026-10-19T05:00:00Z',
                  required_count: 3,
                  verified_count: 1,
                },
              ]
            : [
                {
                  kind: 'BUSINESS',
                  id: 'b1',
                  name: 'TECHBIGGIEY TRADERS',
                  status: 'UNVERIFIED',
                  open_count: 1,
                  oldest_open_at: '2026-10-19T06:00:00Z',
                  created_at: '2026-10-19T05:00:00Z',
                },
              ],
        page,
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<VerificationQueuePage />, { route: '/verification' });

    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual(['Operators', 'Businesses', 'Groups']);
    const row = await screen.findByRole('link', { name: /BIGG-MOVERS/ });
    expect(row).toHaveAttribute('href', '/verification/applicants/OPERATOR/op1');
    expect(row).toHaveTextContent('Awaiting approval');
    expect(row).toHaveTextContent('2 to review');
    expect(row).toHaveTextContent('1 of 3 checks verified');

    await user.click(screen.getByRole('tab', { name: 'Businesses' }));
    expect(await screen.findByRole('link', { name: /TECHBIGGIEY TRADERS/ })).toHaveAttribute(
      'href',
      '/verification/applicants/BUSINESS/b1',
    );
    expect(applicants).toHaveBeenLastCalledWith('BUSINESS');
  });

  it('shows everything an operator submitted, grouped, and approves them', async () => {
    const record = (id: string, domain: string, subject_type: string) => ({
      id,
      subject_type,
      subject_id: 's',
      domain,
      state: 'SUBMITTED',
      effective_state: 'SUBMITTED',
      issuing_authority: '',
      verified_at: null,
      expires_at: null,
      created_at: '2026-10-19T06:00:00Z',
      updated_at: '2026-10-19T06:00:00Z',
      evidence: [
        {
          id: `ev-${id}`,
          evidence_id: 'e',
          kind: domain === 'IDENTITY' ? 'NATIONAL_ID' : 'LOGBOOK',
          content_type: 'image/png',
          pii_class: 'HIGH',
          issued_at: null,
          expires_at: null,
          submitted_at: '2026-10-19T06:00:00Z',
          superseded_at: null,
        },
      ],
      decisions: [],
    });
    applicant.mockResolvedValue({
      kind: 'OPERATOR',
      id: 'op1',
      name: 'BIGG-MOVERS',
      status: 'PENDING',
      open_count: 2,
      oldest_open_at: null,
      created_at: '2026-10-19T05:00:00Z',
      required_count: 3,
      verified_count: 0,
      requirements: [{ domain: 'IDENTITY', mandatory: true, state: 'SUBMITTED' }],
      records: [record('r1', 'IDENTITY', 'OPERATOR')],
      vehicles: [
        {
          id: 'v1',
          registration: 'KDA 123A',
          vehicle_class: 'PICKUP',
          status: 'ACTIVE',
          records: [record('r2', 'VEHICLE', 'VEHICLE')],
        },
      ],
      bases: [],
    });
    approveOperator.mockResolvedValue({ before_state: 'PENDING', after_state: 'ACTIVE' });
    const user = userEvent.setup();
    renderWithProviders(
      <Routes>
        <Route path="/verification/applicants/:kind/:applicantId" element={<ApplicantPage />} />
      </Routes>,
      { route: '/verification/applicants/OPERATOR/op1' },
    );

    expect(await screen.findByRole('heading', { name: 'BIGG-MOVERS' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Identity' })).toBeInTheDocument();
    expect(screen.getByText('National ID')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'KDA 123A · PICKUP' })).toBeInTheDocument();
    expect(screen.getByText('Logbook')).toBeInTheDocument();
    expect(screen.getByText(/Only 0 of 3 required checks are verified/)).toBeInTheDocument();

    await user.type(screen.getByLabelText('Note', { selector: 'input' }), 'Checked in person');
    await user.click(screen.getByRole('button', { name: 'Approve operator' }));
    await waitFor(() => expect(approveOperator).toHaveBeenCalledWith('op1', 'Checked in person'));
  });
});
