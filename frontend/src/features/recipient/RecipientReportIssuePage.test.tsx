import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { RecipientReportIssuePage } from './RecipientReportIssuePage';

const reportIssue = vi.fn();

vi.mock('@/features/jobs/recipientApi', () => ({
  recipientApi: { reportIssue: (...a: unknown[]) => reportIssue(...a) },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
  URL.revokeObjectURL = vi.fn();
});

function renderAtToken(token: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/r/:token/report-issue" element={<RecipientReportIssuePage />} />
    </Routes>,
    { route: `/r/${token}/report-issue` },
  );
}

describe('RecipientReportIssuePage', () => {
  beforeEach(() => {
    reportIssue.mockReset();
  });

  it('the "Other" text field only appears once Other is selected, and is required to submit', async () => {
    const user = userEvent.setup();
    renderAtToken('tok123');

    const submit = screen.getByRole('button', { name: 'Send' });
    expect(submit).toBeDisabled();
    expect(screen.queryByLabelText('Describe the problem')).not.toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: 'Damage' }));
    expect(submit).toBeEnabled();

    await user.click(screen.getByRole('radio', { name: 'Other' }));
    expect(submit).toBeDisabled();
    await user.type(screen.getByLabelText('Describe the problem'), 'Left at the wrong gate');
    expect(submit).toBeEnabled();
  });

  it('submits the selected category with a photo, then shows a focused success confirmation', async () => {
    reportIssue.mockResolvedValue({ report_id: 'r1', category: 'DAMAGE' });
    const user = userEvent.setup();
    renderAtToken('tok123');

    await user.click(screen.getByRole('radio', { name: 'Damage' }));
    await user.type(screen.getByLabelText('Description (optional)'), 'Box was crushed');

    const file = new File(['x'], 'damage.jpg', { type: 'image/jpeg' });
    await user.upload(screen.getByLabelText('Add a photo', { selector: 'input' }), file);

    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(reportIssue).toHaveBeenCalledWith('tok123', {
      category: 'DAMAGE',
      description: 'Box was crushed',
      other_label: undefined,
      photos: [file],
    });

    const success = await screen.findByText('Reported — Fikisha has your report');
    expect(success).toHaveFocus();
  });
});
