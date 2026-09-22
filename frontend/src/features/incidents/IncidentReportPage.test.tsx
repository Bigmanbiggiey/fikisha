import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { renderWithProviders } from '@/test/renderWithProviders';

import { IncidentReportPage } from './IncidentReportPage';

const report = vi.fn();
const attachEvidence = vi.fn();

vi.mock('./incidentsApi', () => ({
  incidentsApi: {
    report: (...a: unknown[]) => report(...a),
    attachEvidence: (...a: unknown[]) => attachEvidence(...a),
  },
}));
vi.mock('@/features/auth/authApi', () => ({
  authApi: { me: () => Promise.reject(new Error('anon')), logout: vi.fn() },
}));

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
  URL.revokeObjectURL = vi.fn();
});

function renderAtJob(jobId: string): ReturnType<typeof renderWithProviders> {
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:jobId/report-issue" element={<IncidentReportPage />} />
      <Route path="/incidents/:incidentId" element={<div>Incident detail screen</div>} />
    </Routes>,
    { route: `/jobs/${jobId}/report-issue` },
  );
}

describe('IncidentReportPage', () => {
  beforeEach(() => {
    report.mockReset();
    attachEvidence.mockReset();
  });

  it('submit stays disabled until a category is picked, and OTHER requires a description', async () => {
    const user = userEvent.setup();
    renderAtJob('job1');

    const submit = screen.getByRole('button', { name: 'Submit' });
    expect(submit).toBeDisabled();

    await user.click(screen.getByRole('radio', { name: 'Damage' }));
    expect(submit).toBeEnabled();

    await user.click(screen.getByRole('radio', { name: 'Other' }));
    expect(submit).toBeDisabled();
    await user.type(screen.getByLabelText('Tell us what kind of issue this is'), 'Something unusual');
    expect(submit).toBeEnabled();
  });

  it('reports the incident, attaches a photo, then navigates to the incident detail screen', async () => {
    report.mockResolvedValue({ id: 'inc1', job_id: 'job1' });
    attachEvidence.mockResolvedValue({ id: 'ev1', evidence_object_id: 'eo1' });
    const user = userEvent.setup();
    renderAtJob('job1');

    await user.click(screen.getByRole('radio', { name: 'Breakdown' }));

    const file = new File(['x'], 'proof.jpg', { type: 'image/jpeg' });
    await user.upload(screen.getByLabelText('Add a photo', { selector: 'input' }), file);

    await user.click(screen.getByRole('button', { name: 'Submit' }));

    expect(report).toHaveBeenCalledWith(
      'job1',
      { type: 'BREAKDOWN', description: undefined, other_label: undefined },
      expect.any(String),
    );
    expect(attachEvidence).toHaveBeenCalledWith('inc1', file);
    expect(await screen.findByText('Incident detail screen')).toBeInTheDocument();
  });
});
