import { Navigate, Route, Routes } from 'react-router-dom';

import { LoginPage } from '@/features/auth/LoginPage';
import { RequireAuth } from '@/features/auth/RequireAuth';
import { DiagnosticsPage } from '@/features/diagnostics/DiagnosticsPage';
import { HomePage } from '@/features/home/HomePage';
import { BusinessDetailPage } from '@/features/org/BusinessDetailPage';
import { BusinessesPage } from '@/features/org/BusinessesPage';
import { GroupDetailPage } from '@/features/org/GroupDetailPage';
import { GroupsPage } from '@/features/org/GroupsPage';
import { OperatingLocationsPage } from '@/features/org/OperatingLocationsPage';
import { OperatorProfilePage } from '@/features/org/OperatorProfilePage';
import { AppShell } from '@/shell/AppShell';

export function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="businesses" element={<BusinessesPage />} />
        <Route path="businesses/:businessId" element={<BusinessDetailPage />} />
        <Route path="operator" element={<OperatorProfilePage />} />
        <Route path="groups" element={<GroupsPage />} />
        <Route path="groups/:groupId" element={<GroupDetailPage />} />
        <Route path="operating-locations" element={<OperatingLocationsPage />} />
        <Route path="diagnostics" element={<DiagnosticsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
