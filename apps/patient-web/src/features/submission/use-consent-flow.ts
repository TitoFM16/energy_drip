import { useContext } from 'react';
import { ConsentFlowContext, type ConsentFlowState } from './consent-flow-context';

export function useConsentFlow(): ConsentFlowState {
  const context = useContext(ConsentFlowContext);
  if (!context) {
    throw new Error('useConsentFlow must be used within a ConsentFlowProvider');
  }
  return context;
}
