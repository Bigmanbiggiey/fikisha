import { QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';
import { BrowserRouter } from 'react-router-dom';

import { AuthProvider } from '@/features/auth/AuthProvider';
import i18n from '@/i18n';

import { ErrorBoundary } from './ErrorBoundary';
import { createQueryClient } from './queryClient';

export function AppProviders({ children }: { children: ReactNode }): JSX.Element {
  const [queryClient] = useState(createQueryClient);

  return (
    <ErrorBoundary>
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AuthProvider>{children}</AuthProvider>
          </BrowserRouter>
        </QueryClientProvider>
      </I18nextProvider>
    </ErrorBoundary>
  );
}
