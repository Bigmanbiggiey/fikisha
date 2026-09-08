import { Navigate, Route, Routes } from 'react-router-dom';

import { LoginPage } from '@/features/auth/LoginPage';
import { RequireAuth } from '@/features/auth/RequireAuth';
import { DiagnosticsPage } from '@/features/diagnostics/DiagnosticsPage';
import { HomePage } from '@/features/home/HomePage';
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
        <Route path="diagnostics" element={<DiagnosticsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
