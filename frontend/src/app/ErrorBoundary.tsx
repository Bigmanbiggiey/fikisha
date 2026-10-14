import { Component, type ErrorInfo, type ReactNode } from 'react';

import i18n from '@/i18n';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Last-resort UI guard. Keeps a render error from blanking the whole app;
 * it does not report anywhere in Phase 2A (Sentry wiring is backend-only so far).
 * It sits outside the I18nextProvider, so it reads the i18n instance
 * directly (P-05).
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Unhandled UI error', error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="mx-auto max-w-md px-4 py-16 text-center">
          <h1 className="text-h2 text-fg">{i18n.t('common:errorBoundary.title')}</h1>
          <p className="mt-2 text-body-sm text-fg-muted">{i18n.t('common:errorBoundary.body')}</p>
          <button
            type="button"
            className="mt-4 inline-flex min-h-target items-center justify-center rounded-md bg-action-primary px-4 text-body font-semibold text-action-on-primary"
            onClick={() => window.location.reload()}
          >
            {i18n.t('common:actions.reload')}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
