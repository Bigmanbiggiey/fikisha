import { AppProviders } from './app/providers';
import { AppRoutes } from './app/router';

export function App(): JSX.Element {
  return (
    <AppProviders>
      <AppRoutes />
    </AppProviders>
  );
}
