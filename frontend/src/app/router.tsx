import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import { LoginPage } from '@/features/auth/LoginPage';
import { RequireAuth } from '@/features/auth/RequireAuth';
import { DiagnosticsPage } from '@/features/diagnostics/DiagnosticsPage';
import { HomePage } from '@/features/home/HomePage';
import { AssignDriverVehiclePage } from '@/features/jobs/AssignDriverVehiclePage';
import { CreateJobPage } from '@/features/jobs/CreateJobPage';
import { CustodyConfirmationPage } from '@/features/jobs/CustodyConfirmationPage';
import { DeliveryProofPage } from '@/features/jobs/DeliveryProofPage';
import { JobDetailPage } from '@/features/jobs/JobDetailPage';
import { JobOpportunityPage } from '@/features/jobs/JobOpportunityPage';
import { JobsListPage } from '@/features/jobs/JobsListPage';
import { MyJobsPage } from '@/features/jobs/MyJobsPage';
import { PickupConfirmPage } from '@/features/jobs/PickupConfirmPage';
import { PickupProofPage } from '@/features/jobs/PickupProofPage';
import { WorkListPage } from '@/features/jobs/WorkListPage';
import { HomeOrLanding } from '@/features/landing/HomeOrLanding';
import { NegotiationPage } from '@/features/negotiation/NegotiationPage';
import { BusinessDetailPage } from '@/features/org/BusinessDetailPage';
import { BusinessesPage } from '@/features/org/BusinessesPage';
import { GroupDetailPage } from '@/features/org/GroupDetailPage';
import { GroupsPage } from '@/features/org/GroupsPage';
import { OperatingLocationsPage } from '@/features/org/OperatingLocationsPage';
import { OperatorProfilePage } from '@/features/org/OperatorProfilePage';
import { RecipientConfirmPage } from '@/features/recipient/RecipientConfirmPage';
import { RecipientPage } from '@/features/recipient/RecipientPage';
import { RecipientReportIssuePage } from '@/features/recipient/RecipientReportIssuePage';
import { VehicleDetailPage } from '@/features/vehicles/VehicleDetailPage';
import { VehiclesPage } from '@/features/vehicles/VehiclesPage';
import { VerificationQueuePage } from '@/features/verification/VerificationQueuePage';
import { VerificationRecordPage } from '@/features/verification/VerificationRecordPage';
import { AppShell } from '@/shell/AppShell';

/**
 * `/` is public (the landing page for a signed-out or first-time visitor —
 * `HomeOrLanding` sends an already-authenticated visitor on to `/home`).
 * Everything else that touches account data stays behind `RequireAuth`,
 * which redirects to `/login` and back (`state.from`) — a new user is only
 * ever prompted to sign in once they reach a route that actually needs it.
 */
export function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      {/* Recipient scoped-link routes — no account, token-in-URL auth, no
          AppShell/TopBar and no RequireAuth (mirrors the /login precedent
          above as the one other chrome-free public route). */}
      <Route path="/r/:token" element={<RecipientPage />} />
      <Route path="/r/:token/confirm" element={<RecipientConfirmPage />} />
      <Route path="/r/:token/report-issue" element={<RecipientReportIssuePage />} />
      <Route element={<AppShell />}>
        <Route index element={<HomeOrLanding />} />
        <Route
          element={
            <RequireAuth>
              <Outlet />
            </RequireAuth>
          }
        >
          <Route path="home" element={<HomePage />} />
          <Route path="jobs" element={<JobsListPage />} />
          <Route path="jobs/new" element={<CreateJobPage />} />
          <Route path="jobs/:jobId" element={<JobDetailPage />} />
          <Route path="jobs/:jobId/confirm-pickup" element={<PickupConfirmPage />} />
          <Route path="jobs/:jobId/negotiation" element={<NegotiationPage />} />
          <Route path="jobs/:jobId/assign" element={<AssignDriverVehiclePage />} />
          <Route path="jobs/:jobId/pickup-proof" element={<PickupProofPage />} />
          <Route path="jobs/:jobId/custody-confirmation" element={<CustodyConfirmationPage />} />
          <Route path="jobs/:jobId/delivery-proof" element={<DeliveryProofPage />} />
          <Route path="work" element={<WorkListPage />} />
          <Route path="work/:jobId" element={<JobOpportunityPage />} />
          <Route path="my-jobs" element={<MyJobsPage />} />
          <Route path="businesses" element={<BusinessesPage />} />
          <Route path="businesses/:businessId" element={<BusinessDetailPage />} />
          <Route path="operator" element={<OperatorProfilePage />} />
          <Route path="groups" element={<GroupsPage />} />
          <Route path="groups/:groupId" element={<GroupDetailPage />} />
          <Route path="operating-locations" element={<OperatingLocationsPage />} />
          <Route path="vehicles" element={<VehiclesPage />} />
          <Route path="vehicles/:vehicleId" element={<VehicleDetailPage />} />
          <Route path="verification" element={<VerificationQueuePage />} />
          <Route path="verification/:recordId" element={<VerificationRecordPage />} />
          <Route path="diagnostics" element={<DiagnosticsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
