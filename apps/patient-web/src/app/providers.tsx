import { QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ConsentFlowProvider } from '../features/submission/consent-flow-context';
import { queryClient } from './query-client';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ConsentFlowProvider>{children}</ConsentFlowProvider>
    </QueryClientProvider>
  );
}
