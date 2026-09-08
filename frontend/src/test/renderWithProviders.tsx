import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';

import { AuthProvider } from '@/features/auth/AuthProvider';
import i18n from '@/i18n';

interface Options {
  route?: string;
  withAuth?: boolean;
}

export function renderWithProviders(ui: ReactElement, options: Options = {}): RenderResult {
  const { route = '/', withAuth = true } = options;
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const Wrapped = ({ children }: { children: ReactNode }): JSX.Element => (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>
          {withAuth ? <AuthProvider>{children}</AuthProvider> : children}
        </MemoryRouter>
      </QueryClientProvider>
    </I18nextProvider>
  );

  return render(ui, { wrapper: Wrapped });
}
