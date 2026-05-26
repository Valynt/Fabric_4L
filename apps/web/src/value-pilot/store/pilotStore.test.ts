import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePilotStore } from './pilotStore';

describe('pilotStore', () => {
  beforeEach(() => {
    usePilotStore.getState().clearSession();
    vi.useRealTimers();
  });

  it('initializes and clears session state', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-02-01T00:00:00.000Z'));

    const store = usePilotStore.getState();
    expect(store.sessionId).toBeNull();
    store.initSession();
    const started = usePilotStore.getState();
    expect(started.sessionId).toMatch(/^pilot_/);
    expect(started.startedAt).toBe('2026-02-01T00:00:00.000Z');

    store.clearSession();
    expect(usePilotStore.getState().sessionId).toBeNull();
    expect(usePilotStore.getState().currentStep).toBe(0);
  });

  it('guards step bounds and deduplicates selections', () => {
    const store = usePilotStore.getState();
    store.setCurrentStep(999);
    expect(usePilotStore.getState().currentStep).toBe(6);
    store.setCurrentStep(-8);
    expect(usePilotStore.getState().currentStep).toBe(0);

    store.selectHypothesis('h1');
    store.selectHypothesis('h1');
    expect(usePilotStore.getState().selectedHypothesisIds).toEqual(['h1']);

    store.selectNode('n1');
    store.selectNode('n1');
    expect(usePilotStore.getState().selectedNodeIds).toEqual(['n1']);
  });

  it('supports partial prospect/scenario updates and stale-state guards', () => {
    const store = usePilotStore.getState();
    store.updateProspect({ companyName: 'ignored' } as never);
    expect(usePilotStore.getState().prospect).toBeNull();

    store.setProspect({ companyId: 'c1', companyName: 'Acme', contactName: 'Jane', contactTitle: 'Director' } as never);
    store.updateProspect({ companyName: 'Acme 2' } as never);
    expect(usePilotStore.getState().prospect).toMatchObject({ companyId: 'c1', companyName: 'Acme 2' });

    store.updateVariable('var-1', { value: 12 } as never);
    expect(usePilotStore.getState().scenario).toBeNull();
  });

  it('computes canProceed selector per step prerequisites', () => {
    const store = usePilotStore.getState();

    store.setCurrentStep(0);
    expect(usePilotStore.getState().canProceed).toBe(false);

    store.setCurrentStep(1);
    expect(usePilotStore.getState().canProceed).toBe(false);
    store.setEnrichedEntities([{ id: 'e1' }] as never);
    // selector remains tied to strict store preconditions; regression guard keeps current behavior explicit
    expect(usePilotStore.getState().canProceed).toBe(false);

    store.setCurrentStep(4);
    expect(usePilotStore.getState().canProceed).toBe(false);
  });
});
